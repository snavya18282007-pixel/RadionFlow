from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.radiology_classifier import normalize_report_text  # noqa: E402

DEFAULT_REPORTS_DIR = PROJECT_ROOT / "data" / "reports"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "data" / "radiology_dataset.csv"
MIN_SAMPLES = 50

NEGATION_PATTERN = re.compile(
    r"(?:no|without|negative for|no evidence of|no radiographic evidence of|free of|unlikely|exclude|excluded|rule out|r/o)",
    re.IGNORECASE,
)

MESH_LABEL_PATTERNS: dict[str, tuple[str, ...]] = {
    "tuberculosis": (
        r"tuberculosis",
        r"granulomatous disease",
    ),
    "pneumonia": (r"pneumonia",),
    "lung_cancer": (
        r"lung neoplasm",
        r"lung cancer",
        r"bronchogenic carcinoma",
        r"carcinoma",
        r"malignancy",
    ),
    "pleural_effusion": (r"pleural effusion",),
    "cardiomegaly": (r"cardiomegaly",),
    "normal": (r"normal",),
}

TEXT_LABEL_PATTERNS: dict[str, tuple[str, ...]] = {
    "tuberculosis": (
        r"\bactive tuberculosis\b",
        r"\bconsistent with tuberculosis\b",
        r"\bcompatible with tuberculosis\b",
        r"\bpossibility of tuberculosis\b",
        r"\bprior tb\b",
        r"\bprior tuberculosis\b",
        r"\bcavitary lesion\b",
        r"\bcavitary opacity\b",
        r"\bfibrocavitary\b",
        r"\bapical pleural thickening\b",
        r"\bupper lobe infiltrate\b",
        r"\bgranulomatous disease\b",
    ),
    "pneumonia": (
        r"\bpneumonia\b",
        r"\bbronchopneumonia\b",
        r"\bfocal consolidation\b",
        r"\blobar consolidation\b",
        r"\bmultifocal pneumonia\b",
        r"\bpatchy infiltrate\b",
        r"\bairspace opacity\b",
        r"\bairspace consolidation\b",
        r"\bbibasilar consolidation\b",
    ),
    "lung_cancer": (
        r"\blung cancer\b",
        r"\blung neoplasm\b",
        r"\bbronchogenic carcinoma\b",
        r"\bspiculated mass\b",
        r"\bspiculated nodule\b",
        r"\bpulmonary mass\b",
        r"\bhilar mass\b",
        r"\bsuspicious for malignancy\b",
        r"\benlarging nodule\b",
    ),
    "pleural_effusion": (
        r"\bpleural effusion\b",
        r"\bcostophrenic blunting\b",
        r"\bblunting of the costophrenic\b",
    ),
    "cardiomegaly": (
        r"\bcardiomegaly\b",
        r"\benlarged cardiac silhouette\b",
        r"\bheart is enlarged\b",
        r"\bcardiac silhouette is enlarged\b",
        r"\bmildly enlarged heart\b",
    ),
    "normal": (
        r"\bnormal chest\b",
        r"\bno acute cardiopulmonary abnormality\b",
        r"\bno acute cardiopulmonary process\b",
        r"\bno acute disease\b",
    ),
}

LABEL_PRIORITY = (
    "tuberculosis",
    "lung_cancer",
    "pneumonia",
    "pleural_effusion",
    "cardiomegaly",
    "normal",
)


@dataclass(frozen=True)
class PreparedRow:
    report_text: str
    disease_label: str


def extract_report_text(root: ET.Element) -> str:
    sections: list[str] = []
    for node in root.findall(".//AbstractText"):
        if (node.attrib.get("Label") or "").upper() not in {"FINDINGS", "IMPRESSION"}:
            continue
        text = (node.text or "").strip()
        if text:
            sections.append(text)
    return " ".join(sections).strip()


def extract_mesh_terms(root: ET.Element) -> list[str]:
    values: list[str] = []
    for xpath in (".//DescriptorName", ".//MeSH/major", ".//major"):
        for node in root.findall(xpath):
            text = (node.text or "").strip().lower()
            if text:
                values.append(text)
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def is_negated(text: str, matched_phrase: str) -> bool:
    escaped_phrase = re.escape(matched_phrase)
    pattern = re.compile(rf"{NEGATION_PATTERN.pattern}[^.\n]{{0,60}}{escaped_phrase}", re.IGNORECASE)
    return bool(pattern.search(text))


def mesh_label_candidates(mesh_terms: list[str]) -> list[str]:
    matches: list[str] = []
    for term in mesh_terms:
        for label, patterns in MESH_LABEL_PATTERNS.items():
            if any(re.search(pattern, term) for pattern in patterns):
                matches.append(label)
    ordered: list[str] = []
    seen: set[str] = set()
    for label in matches:
        if label in seen:
            continue
        seen.add(label)
        ordered.append(label)
    return ordered


def infer_labels_from_text(report_text: str) -> list[str]:
    normalized_text = normalize_report_text(report_text)
    matches: list[str] = []
    for label in LABEL_PRIORITY:
        for pattern in TEXT_LABEL_PATTERNS.get(label, ()):
            for match in re.finditer(pattern, normalized_text, re.IGNORECASE):
                phrase = match.group(0).strip()
                if is_negated(normalized_text, phrase):
                    continue
                matches.append(label)

    ordered: list[str] = []
    seen: set[str] = set()
    for label in matches:
        if label in seen:
            continue
        seen.add(label)
        ordered.append(label)
    return ordered


def assign_label(report_text: str, mesh_terms: list[str]) -> str | None:
    mesh_candidates = mesh_label_candidates(mesh_terms)
    text_candidates = infer_labels_from_text(report_text)

    combined_candidates: list[str] = []
    for label in LABEL_PRIORITY:
        if label in mesh_candidates or label in text_candidates:
            combined_candidates.append(label)

    # Keep only clinically cleaner single-label cases for training.
    if len(combined_candidates) != 1:
        return None
    return combined_candidates[0]


def prepare_dataset(
    reports_dir: Path,
    output_path: Path,
    *,
    min_samples: int = MIN_SAMPLES,
) -> tuple[list[PreparedRow], dict[str, int], dict[str, int]]:
    prepared_rows: list[PreparedRow] = []
    raw_counts: Counter[str] = Counter()

    for path in sorted(reports_dir.glob("*.xml")):
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError:
            continue

        report_text = extract_report_text(root)
        if not report_text:
            continue

        mesh_terms = extract_mesh_terms(root)
        label = assign_label(report_text, mesh_terms)
        if not label:
            continue

        raw_counts[label] += 1
        prepared_rows.append(PreparedRow(report_text=report_text, disease_label=label))

    filtered_labels = {label for label, count in raw_counts.items() if count >= min_samples}
    filtered_rows = [row for row in prepared_rows if row.disease_label in filtered_labels]
    filtered_counts = Counter(row.disease_label for row in filtered_rows)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["report_text", "disease_label"])
        writer.writeheader()
        for row in filtered_rows:
            writer.writerow({"report_text": row.report_text, "disease_label": row.disease_label})

    return filtered_rows, dict(raw_counts), dict(filtered_counts)


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a simplified radiology dataset from NLMCXR XML reports.")
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=DEFAULT_REPORTS_DIR,
        help="Directory containing XML reports.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="CSV output path for the prepared dataset.",
    )
    parser.add_argument(
        "--min-samples",
        type=int,
        default=MIN_SAMPLES,
        help="Minimum samples per class to keep in the saved dataset.",
    )
    args = parser.parse_args()

    rows, raw_counts, filtered_counts = prepare_dataset(
        args.reports_dir,
        args.output,
        min_samples=args.min_samples,
    )

    print(
        json.dumps(
            {
                "reports_dir": str(args.reports_dir),
                "output_path": str(args.output),
                "rows_saved": len(rows),
                "raw_label_counts": raw_counts,
                "filtered_label_counts": filtered_counts,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

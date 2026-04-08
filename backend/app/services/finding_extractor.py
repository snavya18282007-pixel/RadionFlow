from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.ai_model_service import AIModelService, Finding, get_model_service
from app.services.negation_processor import process_radiology_text


BODY_REGION_PATTERNS: dict[str, tuple[str, ...]] = {
    "chest": (r"\bchest\b", r"\blung\b", r"\bpleural\b", r"\bcardiomediastinal\b", r"\bthorax\b"),
    "brain": (r"\bbrain\b", r"\bmri\b", r"\bintracranial\b", r"\bparenchyma\b"),
    "abdomen": (r"\babdomen\b", r"\bhepatic\b", r"\bliver\b", r"\bpelvis\b"),
    "extremity": (r"\bfracture\b", r"\bfemur\b", r"\bhumerus\b", r"\bradius\b", r"\bhand\b"),
}

SEVERITY_PATTERNS: tuple[str, ...] = (
    "mild",
    "moderate",
    "severe",
    "small",
    "large",
    "massive",
    "extensive",
    "diffuse",
    "suspicious",
    "spiculated",
)

FINDING_PATTERNS: dict[str, tuple[str, ...]] = {
    "pleural effusion": (r"\bpleural effusion\b", r"\beffusion\b"),
    "consolidation": (r"\bconsolidation\b", r"\bairspace opacity\b", r"\bairspace consolidation\b"),
    "pneumonia": (r"\bpneumonia\b", r"\bbronchopneumonia\b", r"\binfiltrate\b"),
    "mass": (r"\bmass\b", r"\bspiculated mass\b", r"\bmass lesion\b"),
    "nodule": (r"\bnodule\b", r"\bspiculated nodule\b", r"\bpulmonary nodule\b"),
    "fracture": (r"\bfracture\b", r"\bfractured\b"),
    "opacity": (r"\bopacity\b", r"\bopacities\b"),
    "tuberculosis": (
        r"\btuberculosis\b",
        r"\btb\b",
        r"\bcavitary lesion\b",
        r"\bapical pleural thickening\b",
        r"\bupper lobe infiltrate\b",
    ),
    "pneumothorax": (r"\bpneumothorax\b",),
    "cardiomegaly": (r"\bcardiomegaly\b", r"\benlarged cardiac silhouette\b"),
}


@dataclass(frozen=True)
class ExtractedFinding:
    label: str
    confidence: float
    evidence: str | None = None


@dataclass(frozen=True)
class FindingExtractionResult:
    findings: list[str]
    body_region: str
    severity_terms: list[str]
    positive_findings: list[str]
    negated_findings: list[str]
    entities: list[ExtractedFinding]
    summary: str
    cleaned_text: str
    negation_engine: str
    all_findings_negated: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "findings": self.findings,
            "body_region": self.body_region,
            "severity_terms": self.severity_terms,
            "positive_findings": self.positive_findings,
            "negated_findings": self.negated_findings,
            "summary": self.summary,
            "negation_engine": self.negation_engine,
            "all_findings_negated": self.all_findings_negated,
        }


def _unique_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _normalize_finding(label: str) -> str:
    normalized = label.strip().lower()
    alias_map = {
        "effusion": "pleural effusion",
        "pulmonary nodule": "nodule",
        "pulmonary mass": "mass",
        "lung mass": "mass",
        "airspace opacity": "opacity",
        "airspace consolidation": "consolidation",
        "tb": "tuberculosis",
        "mass lesion": "mass",
    }
    return alias_map.get(normalized, normalized)


def _detect_body_region(text: str) -> str:
    for region, patterns in BODY_REGION_PATTERNS.items():
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns):
            return region
    return "chest"


def _detect_severity_terms(text: str) -> list[str]:
    matches = [term for term in SEVERITY_PATTERNS if re.search(rf"\b{re.escape(term)}\b", text, re.IGNORECASE)]
    return _unique_preserve_order(matches)


def _collect_rule_matches(text: str) -> list[ExtractedFinding]:
    extracted: list[ExtractedFinding] = []
    for label, patterns in FINDING_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                extracted.append(
                    ExtractedFinding(
                        label=label,
                        confidence=0.9 if label in {"tuberculosis", "pneumothorax"} else 0.84,
                        evidence=match.group(0),
                    )
                )
                break
    return extracted


def _fallback_model_findings(model_service: AIModelService, text: str) -> list[ExtractedFinding]:
    findings = []
    for item in model_service.extract_findings(text):
        normalized_label = _normalize_finding(item.label)
        if normalized_label == "no acute findings":
            continue
        findings.append(
            ExtractedFinding(
                label=normalized_label,
                confidence=item.confidence,
                evidence=item.evidence,
            )
        )
    return findings


def extract_findings(report_text: str, model_service: AIModelService | None = None) -> FindingExtractionResult:
    service = model_service or get_model_service()
    negation_result = process_radiology_text(report_text)
    cleaned_text = negation_result.cleaned_text or report_text

    positive_findings = [_normalize_finding(item) for item in negation_result.positive_findings]
    negated_findings = [_normalize_finding(item) for item in negation_result.negated_findings]
    severity_terms = _detect_severity_terms(report_text)
    body_region = _detect_body_region(report_text)

    rule_entities = _collect_rule_matches(cleaned_text)
    if not rule_entities and not negation_result.all_findings_negated:
        rule_entities = _fallback_model_findings(service, cleaned_text)

    merged_entities: list[ExtractedFinding] = []
    seen_labels: set[str] = set()
    for finding in [*rule_entities, *[ExtractedFinding(label=item, confidence=0.92, evidence=item) for item in positive_findings]]:
        normalized_label = _normalize_finding(finding.label)
        if normalized_label in seen_labels:
            continue
        seen_labels.add(normalized_label)
        merged_entities.append(
            ExtractedFinding(
                label=normalized_label,
                confidence=finding.confidence,
                evidence=finding.evidence,
            )
        )

    findings = _unique_preserve_order([item.label for item in merged_entities] + positive_findings)
    positive_findings = _unique_preserve_order(findings)
    negated_findings = _unique_preserve_order(negated_findings)

    summary = "; ".join(positive_findings) if positive_findings else "No positive findings after negation detection."

    return FindingExtractionResult(
        findings=positive_findings,
        body_region=body_region,
        severity_terms=severity_terms,
        positive_findings=positive_findings,
        negated_findings=negated_findings,
        entities=merged_entities,
        summary=summary,
        cleaned_text=cleaned_text,
        negation_engine=negation_result.engine,
        all_findings_negated=negation_result.all_findings_negated,
    )

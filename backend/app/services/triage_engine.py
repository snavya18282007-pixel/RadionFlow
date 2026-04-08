from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.services.radiology_classifier import normalize_label_name


URGENCY_LEVELS = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
LEVEL_TO_PRIORITY_SCORE = {
    "LOW": 0.12,
    "MEDIUM": 0.42,
    "HIGH": 0.72,
    "CRITICAL": 0.95,
}

DISEASE_BASELINE_URGENCY = {
    "normal": "LOW",
    "cardiomegaly": "MEDIUM",
    "pleural_effusion": "MEDIUM",
    "pneumonia": "HIGH",
    "tuberculosis": "HIGH",
    "lung_cancer": "HIGH",
    "lung_mass": "HIGH",
    "fracture": "HIGH",
    "other_lung_abnormality": "MEDIUM",
}

FINDING_URGENCY_HINTS = {
    "pneumothorax": "CRITICAL",
    "mass": "HIGH",
    "nodule": "MEDIUM",
    "pleural effusion": "MEDIUM",
    "consolidation": "HIGH",
    "pneumonia": "HIGH",
    "tuberculosis": "HIGH",
    "opacity": "MEDIUM",
    "cardiomegaly": "MEDIUM",
    "fracture": "HIGH",
}

CRITICAL_SEVERITY_TERMS = {"severe", "large", "massive", "extensive", "suspicious", "spiculated"}


def _urgency_rank(level: str) -> int:
    return URGENCY_LEVELS.index(level)


def _unique_levels(levels: Iterable[str]) -> list[str]:
    return [level for level in levels if level in URGENCY_LEVELS]


def confidence_adjustment(confidence: float) -> int:
    if confidence < 0.35:
        return -1
    if confidence >= 0.92:
        return 1
    return 0


def _bounded_level(index: int) -> str:
    return URGENCY_LEVELS[max(0, min(index, len(URGENCY_LEVELS) - 1))]


def display_name(disease: str) -> str:
    return disease.replace("_", " ").title()


def calculate_urgency(
    disease: str,
    findings: list[str],
    *,
    severity_terms: list[str] | None = None,
    confidence: float = 0.0,
) -> str:
    normalized_disease = normalize_label_name(disease)
    normalized_findings = {normalize_label_name(item).replace("_", " ") for item in findings}
    severity = {item.lower() for item in (severity_terms or [])}

    if normalized_disease == "normal" and not normalized_findings:
        return "LOW"

    if "pneumothorax" in normalized_findings:
        return "CRITICAL"

    if "consolidation" in normalized_findings and severity & {"severe", "extensive"}:
        return "CRITICAL"

    if "pleural effusion" in normalized_findings and severity & {"large", "massive"}:
        return "CRITICAL"

    if normalized_disease in {"lung_cancer", "lung_mass"} and severity & {"suspicious", "spiculated"}:
        return "CRITICAL"

    levels = [
        DISEASE_BASELINE_URGENCY.get(normalized_disease, "MEDIUM"),
        *[FINDING_URGENCY_HINTS[item] for item in normalized_findings if item in FINDING_URGENCY_HINTS],
    ]
    baseline = max(_unique_levels(levels), key=_urgency_rank, default="MEDIUM")
    adjusted = _bounded_level(_urgency_rank(baseline) + confidence_adjustment(confidence))

    if normalized_disease == "normal":
        return "LOW"
    return adjusted


def priority_score_for_urgency(urgency: str, confidence: float) -> float:
    severity_score = LEVEL_TO_PRIORITY_SCORE[urgency]
    return round((severity_score * 0.75) + (max(0.0, min(1.0, confidence)) * 0.25), 3)


@dataclass(frozen=True)
class TriageResult:
    urgency_category: str
    priority_score: float
    recommended_review_minutes: int
    rationale: str

    def to_dict(self) -> dict:
        return {
            "urgency_category": self.urgency_category,
            "priority_score": round(self.priority_score, 3),
            "recommended_review_minutes": self.recommended_review_minutes,
            "rationale": self.rationale,
        }


class TriageEngine:
    _level_to_review_minutes = {
        "LOW": 72 * 60,
        "MEDIUM": 24 * 60,
        "HIGH": 2 * 60,
        "CRITICAL": 15,
    }

    def compute(
        self,
        findings: Iterable[str],
        disease: str,
        confidence: float,
        *,
        severity_terms: Iterable[str] = (),
    ) -> TriageResult:
        findings_list = [item for item in findings if item]
        severity_list = [item for item in severity_terms if item]
        normalized_disease = normalize_label_name(disease)
        urgency = calculate_urgency(
            normalized_disease,
            findings_list,
            severity_terms=severity_list,
            confidence=confidence,
        )

        review_minutes = self._level_to_review_minutes[urgency]
        rationale = (
            f"Triage set to {urgency} for '{display_name(normalized_disease)}' at confidence {confidence:.0%}. "
            f"Positive findings: {findings_list or ['none']}. Severity terms: {severity_list or ['none']}."
        )

        return TriageResult(
            urgency_category=urgency,
            priority_score=priority_score_for_urgency(urgency, confidence),
            recommended_review_minutes=review_minutes,
            rationale=rationale,
        )


def triage_to_json(
    findings: Iterable[str],
    disease: str,
    confidence: float,
    *,
    severity_terms: Iterable[str] = (),
) -> dict:
    engine = TriageEngine()
    return engine.compute(
        findings=findings,
        disease=disease,
        confidence=confidence,
        severity_terms=severity_terms,
    ).to_dict()

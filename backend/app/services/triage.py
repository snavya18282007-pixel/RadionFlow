from __future__ import annotations

from app.schemas.report import TriageResponse
from app.services.triage_engine import TriageEngine


class TriageService:
    def __init__(self) -> None:
        self.engine = TriageEngine()

    def score(
        self,
        disease: str,
        findings_summary: str,
        confidence: float,
        *,
        findings: list[str] | None = None,
        severity_terms: list[str] | None = None,
        negation_only: bool = False,
    ) -> TriageResponse:
        if negation_only:
            return TriageResponse(
                urgency_score=0.12,
                urgency_label="LOW",
                rationale=(
                    "Urgency set to LOW because all detected findings were inside negated clinical phrases, "
                    "so the report is being treated as Normal."
                ),
            )

        triage_result = self.engine.compute(
            findings=findings or ([item.strip() for item in findings_summary.split(";") if item.strip()] if findings_summary else []),
            disease=disease,
            confidence=confidence,
            severity_terms=severity_terms or [],
        )
        return TriageResponse(
            urgency_score=triage_result.priority_score,
            urgency_label=triage_result.urgency_category,
            rationale=triage_result.rationale,
        )

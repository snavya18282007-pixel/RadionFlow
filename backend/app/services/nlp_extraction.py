from __future__ import annotations

from app.services.ai_model_service import AIModelService
from app.schemas.report import FindingItem, FindingsResponse
from app.services.finding_extractor import extract_findings


class NLPExtractionService:
    def __init__(self, model_service: AIModelService) -> None:
        self.model_service = model_service

    def extract(
        self,
        text: str,
        *,
        positive_findings: list[str] | None = None,
        negated_findings: list[str] | None = None,
    ) -> FindingsResponse:
        extracted = extract_findings(text, model_service=self.model_service)
        items = [FindingItem(label=f.label, confidence=f.confidence, evidence=f.evidence) for f in extracted.entities]
        return FindingsResponse(
            entities=items,
            summary=extracted.summary,
            findings=extracted.findings,
            body_region=extracted.body_region,
            severity_terms=extracted.severity_terms,
            positive_findings=positive_findings or extracted.positive_findings,
            negated_findings=negated_findings or extracted.negated_findings,
        )

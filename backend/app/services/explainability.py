from __future__ import annotations

from app.schemas.report import ExplainabilityResponse
from app.services.ai_model_service import AIModelService
from app.services.radiology_classifier import get_radiology_classifier


class ExplainabilityService:
    def __init__(self, model_service: AIModelService) -> None:
        self.model_service = model_service
        self.classifier = get_radiology_classifier()

    def build(
        self,
        text: str,
        evidence: list[str],
        disease: str | None = None,
        *,
        positive_findings: list[str] | None = None,
        negated_findings: list[str] | None = None,
        negation_engine: str | None = None,
    ) -> ExplainabilityResponse:
        positive_findings = positive_findings or []
        negated_findings = negated_findings or []
        top_keywords = self.classifier.top_keywords(text, disease=disease, top_k=5)
        model_insights = self.model_service.explain(text)
        model_insights["top_keywords"] = top_keywords
        model_insights["positive_findings"] = positive_findings
        model_insights["negated_findings"] = negated_findings
        if negation_engine:
            model_insights["negation_engine"] = negation_engine

        combined_evidence = [item for item in evidence if item]
        for keyword in top_keywords:
            if keyword not in combined_evidence:
                combined_evidence.append(keyword)

        return ExplainabilityResponse(
            evidence=combined_evidence,
            top_keywords=top_keywords,
            positive_findings=positive_findings,
            negated_findings=negated_findings,
            model_insights=model_insights,
        )

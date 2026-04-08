from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.schemas.report import ClassificationResponse, ReportProcessResponse
from app.services.ai_model_service import get_model_service
from app.services.classification import DiseaseClassificationService
from app.services.disease_trend_analysis import build_empty_trend_analysis
from app.services.explainability import ExplainabilityService
from app.services.finding_extractor import extract_findings
from app.services.followup import FollowUpService
from app.services.inconsistency import InconsistencyService
from app.services.lifestyle import LifestyleService
from app.services.notification import NotificationService
from app.services.patient_explainer import PatientExplainerService
from app.services.smart_critical_alerts import SmartCriticalAlertsService
from app.services.triage import TriageService


class ReportPipelineService:
    def __init__(self) -> None:
        model_service = get_model_service()
        self.model_service = model_service
        self.classifier = DiseaseClassificationService(model_service)
        self.triage = TriageService()
        self.explainability = ExplainabilityService(model_service)
        self.inconsistency = InconsistencyService()
        self.lifestyle = LifestyleService()
        self.followup = FollowUpService()
        self.patient_explainer = PatientExplainerService()
        self.critical_alerts = SmartCriticalAlertsService()
        self.notification = NotificationService()

    def process(self, report_id, text: str) -> ReportProcessResponse:
        logger = logging.getLogger(__name__)
        try:
            extracted = extract_findings(text, model_service=self.model_service)
            findings = self._build_findings_response(extracted)

            if extracted.all_findings_negated:
                classification = ClassificationResponse(
                    disease="Normal",
                    confidence=0.98,
                    probabilities={"Normal": 0.98, "Other lung abnormality": 0.02},
                    model_source="negation-aware-normal",
                )
                triage = self.triage.score(
                    classification.disease,
                    findings.summary,
                    classification.confidence,
                    findings=findings.findings,
                    severity_terms=findings.severity_terms,
                    negation_only=True,
                )
            else:
                classification = self.classifier.classify(extracted.cleaned_text, findings.findings)
                triage = self.triage.score(
                    classification.disease,
                    findings.summary,
                    classification.confidence,
                    findings=findings.findings,
                    severity_terms=findings.severity_terms,
                )

            evidence = [item.evidence for item in findings.entities if item.evidence]
            explainability = self.explainability.build(
                extracted.cleaned_text,
                evidence,
                classification.disease,
                positive_findings=findings.positive_findings,
                negated_findings=findings.negated_findings,
                negation_engine=extracted.negation_engine,
            )
            inconsistencies = self.inconsistency.detect(text)
            lifestyle = self.lifestyle.recommend(classification.disease)
            follow_up = self.followup.recommend(classification.disease)
            patient_explanation = self.patient_explainer.generate(
                disease=classification.disease,
                findings=findings.findings,
                body_region=findings.body_region,
                urgency_level=triage.urgency_label,
            )
            trend_analysis = build_empty_trend_analysis(classification.disease)
            critical_alerts = self.critical_alerts.build(
                disease=classification.disease,
                findings=findings.findings,
                severity_terms=findings.severity_terms,
                urgency_level=triage.urgency_label,
                confidence=classification.confidence,
                inconsistencies=inconsistencies,
                trend_analysis=trend_analysis,
            )
            notification = self.notification.trigger(triage)
        except Exception as exc:
            logger.exception("Report pipeline failed", exc_info=exc)
            raise RuntimeError("Report analysis failed") from exc

        return ReportProcessResponse(
            report_id=report_id,
            findings=findings,
            classification=classification,
            triage=triage,
            explainability=explainability,
            inconsistencies=inconsistencies,
            lifestyle=lifestyle,
            follow_up=follow_up,
            patient_explanation=patient_explanation,
            trend_analysis=trend_analysis,
            critical_alerts=critical_alerts,
            notification=notification,
            processed_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def _build_findings_response(extracted):
        from app.schemas.report import FindingItem, FindingsResponse

        return FindingsResponse(
            entities=[
                FindingItem(label=item.label, confidence=item.confidence, evidence=item.evidence)
                for item in extracted.entities
            ],
            summary=extracted.summary,
            findings=extracted.findings,
            body_region=extracted.body_region,
            severity_terms=extracted.severity_terms,
            positive_findings=extracted.positive_findings,
            negated_findings=extracted.negated_findings,
        )

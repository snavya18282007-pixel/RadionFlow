from __future__ import annotations

import secrets
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db import Report, ReportResult, TriageCase
from app.repositories.case_repo import CaseRepository
from app.repositories.report_repo import ReportRepository
from app.schemas.case import CaseDetailResponse, TriageQueueCase
from app.schemas.report import ReportProcessResponse, TriageResultSummaryResponse
from app.services.automation import AutomationService
from app.services.disease_trend_analysis import DiseaseTrendAnalysisService
from app.services.patient_guidance import PatientGuidanceService
from app.services.report_pipeline import ReportPipelineService
from app.services.smart_critical_alerts import SmartCriticalAlertsService
from app.services.triage_engine import TriageEngine
from app.utils.errors import BadRequestError, NotFoundError

CASE_STATUS_UPLOADED = "UPLOADED"
CASE_STATUS_AI_ANALYZED = "AI_ANALYZED"
CASE_STATUS_AWAITING_DOCTOR = "AWAITING_DOCTOR"
CASE_STATUS_UNDER_REVIEW = "UNDER_REVIEW"
CASE_STATUS_FINALIZED = "FINALIZED"

TRIAGE_SORT_ORDER = {
    "CRITICAL": 0,
    "HIGH": 1,
    "MEDIUM": 2,
    "LOW": 3,
}


def build_patient_token() -> str:
    return f"PT-{secrets.token_hex(4).upper()}"


def normalize_triage_level(level: str | None) -> str:
    if not level:
        return "LOW"
    if level.upper() == "MODERATE":
        return "MEDIUM"
    return level.upper()


class CaseManagementService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.report_repo = ReportRepository(db)
        self.case_repo = CaseRepository(db)
        self.pipeline = ReportPipelineService()
        self.triage_engine = TriageEngine()
        self.guidance = PatientGuidanceService()
        self.trend_analysis = DiseaseTrendAnalysisService(db)
        self.smart_alerts = SmartCriticalAlertsService()
        self.automation = AutomationService()

    def _build_analysis_response(self, report: Report, result: ReportResult | None) -> ReportProcessResponse | None:
        if not result:
            return None

        return ReportProcessResponse(
            report_id=report.id,
            processed_at=result.created_at,
            findings=result.findings,
            classification=result.classification,
            triage=result.triage,
            explainability=result.explainability,
            inconsistencies=result.inconsistencies,
            lifestyle=result.lifestyle,
            follow_up=result.follow_up,
            patient_explanation=result.patient_explanation or {"summary": "", "key_points": []},
            trend_analysis=result.trend_analysis
            or {
                "disease": result.classification.get("disease", "unknown"),
                "recent_case_count": 0,
                "previous_case_count": 0,
                "critical_case_count": 0,
                "window_days": 14,
                "trend_direction": "insufficient_data",
                "summary": "Trend analysis was not available for this historical record.",
            },
            critical_alerts=result.critical_alerts or {"triggered": False, "alerts": []},
            notification=result.notification,
        )

    def _build_case_detail(
        self,
        report: Report,
        triage_case: TriageCase,
        result: ReportResult | None,
    ) -> CaseDetailResponse:
        analysis = self._build_analysis_response(report, result)
        return CaseDetailResponse(
            case_id=triage_case.report_id,
            patient_token=triage_case.patient_token,
            patient_name=triage_case.patient_name,
            patient_email=triage_case.patient_email,
            patient_age=triage_case.patient_age,
            patient_gender=triage_case.patient_gender,
            patient_type=triage_case.patient_type,
            report_status=triage_case.report_status,
            triage_level=triage_case.triage_level,
            predicted_disease=triage_case.predicted_disease,
            confidence_score=triage_case.confidence_score,
            doctor_name=triage_case.doctor_name,
            doctor_notes=triage_case.doctor_notes,
            review_decision=triage_case.review_decision,
            final_diagnosis=triage_case.final_diagnosis,
            patient_explanation=triage_case.patient_explanation,
            lifestyle_guidance=triage_case.lifestyle_guidance or [],
            upload_metadata=triage_case.upload_metadata or {},
            automation_status=triage_case.automation_status or {},
            source_type=report.source_type,
            raw_text=report.raw_text,
            created_at=triage_case.created_at,
            finalized_at=triage_case.finalized_at,
            analysis=analysis,
        )

    def _compute_triage_level(self, report_result: ReportResult) -> str:
        triage = report_result.triage or {}
        triage_label = normalize_triage_level(triage.get("urgency_label"))
        if triage_label in TRIAGE_SORT_ORDER:
            return triage_label

        classification = report_result.classification or {}
        findings = report_result.findings.get("entities", [])
        labels = [item.get("label") for item in findings if isinstance(item, dict) and item.get("label")]
        triage = self.triage_engine.compute(
            findings=labels,
            disease=classification.get("disease", "unknown"),
            confidence=float(classification.get("confidence", 0.0)),
            severity_terms=result.findings.get("severity_terms", []),
        )
        return normalize_triage_level(triage.urgency_category)

    @staticmethod
    def _build_triage_explanation(analysis: ReportProcessResponse) -> str:
        keywords = analysis.explainability.top_keywords or analysis.explainability.evidence
        if keywords:
            evidence_line = ", ".join(keywords[:5])
            return f"{analysis.triage.rationale} Evidence words: {evidence_line}."
        return analysis.triage.rationale

    async def _enrich_analysis_with_context(self, analysis: ReportProcessResponse) -> ReportProcessResponse:
        trend_analysis = await self.trend_analysis.analyze(analysis.classification.disease)
        critical_alerts = self.smart_alerts.build(
            disease=analysis.classification.disease,
            findings=analysis.findings.findings,
            severity_terms=analysis.findings.severity_terms,
            urgency_level=analysis.triage.urgency_label,
            confidence=analysis.classification.confidence,
            inconsistencies=analysis.inconsistencies,
            trend_analysis=trend_analysis,
        )
        return analysis.model_copy(
            update={
                "trend_analysis": trend_analysis,
                "critical_alerts": critical_alerts,
            }
        )

    @staticmethod
    def _analysis_payload(analysis: ReportProcessResponse) -> dict[str, object]:
        return {
            "findings": analysis.findings.model_dump(),
            "classification": analysis.classification.model_dump(),
            "triage": analysis.triage.model_dump(),
            "explainability": analysis.explainability.model_dump(),
            "inconsistencies": analysis.inconsistencies.model_dump(),
            "lifestyle": analysis.lifestyle.model_dump(),
            "follow_up": analysis.follow_up.model_dump(),
            "patient_explanation": analysis.patient_explanation.model_dump(),
            "trend_analysis": analysis.trend_analysis.model_dump(),
            "critical_alerts": analysis.critical_alerts.model_dump(),
            "notification": analysis.notification.model_dump(),
        }

    async def get_case_detail(self, report_id: UUID) -> CaseDetailResponse:
        report = await self.report_repo.get_report(report_id)
        if not report:
            raise NotFoundError("Report not found")

        triage_case = await self.case_repo.get_case(report_id)
        if not triage_case:
            raise NotFoundError("Triage case not found")

        result = await self.report_repo.get_result(report_id)
        if triage_case.report_status == CASE_STATUS_UPLOADED and result is None:
            return await self.analyze_case(report_id)
        return self._build_case_detail(report, triage_case, result)

    async def list_triage_cases(
        self,
        report_status: str | None = None,
        patient_token: str | None = None,
    ) -> list[TriageQueueCase]:
        triage_cases = await self.case_repo.list_cases(report_status=report_status, patient_token=patient_token)
        queue: list[TriageQueueCase] = []

        for triage_case in triage_cases:
            if not triage_case.predicted_disease or triage_case.confidence_score is None or not triage_case.triage_level:
                continue

            queue.append(
                TriageQueueCase(
                    case_id=triage_case.report_id,
                    patient_token=triage_case.patient_token,
                    patient_name=triage_case.patient_name,
                    predicted_disease=triage_case.predicted_disease,
                    confidence_score=triage_case.confidence_score,
                    triage_level=triage_case.triage_level,
                    report_status=triage_case.report_status,
                    created_at=triage_case.created_at,
                )
            )

        queue.sort(
            key=lambda item: (
                TRIAGE_SORT_ORDER.get(item.triage_level, 99),
                -item.confidence_score,
                -item.created_at.timestamp(),
            )
        )
        return queue

    async def group_doctor_cases(self, report_status: str | None = CASE_STATUS_AWAITING_DOCTOR) -> dict[str, list[TriageQueueCase]]:
        queue = await self.list_triage_cases(report_status=report_status)
        grouped = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": [],
        }
        for item in queue:
            grouped[item.triage_level.lower()].append(item)
        return grouped

    async def analyze_case(self, report_id: UUID) -> CaseDetailResponse:
        report = await self.report_repo.get_report(report_id)
        if not report:
            raise NotFoundError("Report not found")

        triage_case = await self.case_repo.get_case(report_id)
        if not triage_case:
            raise NotFoundError("Triage case not found")

        analysis = await self._enrich_analysis_with_context(self.pipeline.process(report.id, report.raw_text))
        payload = self._analysis_payload(analysis)
        await self.report_repo.create_result(report.id, payload)
        result = await self.report_repo.get_result(report.id)
        if not result:
            raise BadRequestError("Analysis result was not persisted")

        triage_level = self._compute_triage_level(result)
        triage_case = await self.case_repo.update_case(
            report.id,
            predicted_disease=result.classification.get("disease", "unknown"),
            confidence_score=float(result.classification.get("confidence", 0.0)),
            triage_level=triage_level,
            report_status=CASE_STATUS_AI_ANALYZED,
        )
        await self.report_repo.update_report(report.id, status=CASE_STATUS_AI_ANALYZED)

        analysis_response = self._build_analysis_response(report, result)
        if not analysis_response:
            raise BadRequestError("Analysis response was not generated")

        await self.report_repo.create_triage_result(
            report.id,
            disease_prediction=result.classification.get("disease", "unknown"),
            confidence_score=float(result.classification.get("confidence", 0.0)),
            urgency_level=triage_level,
            explanation=self._build_triage_explanation(analysis_response),
        )

        triage_case = await self.case_repo.update_case(
            report.id,
            report_status=CASE_STATUS_AWAITING_DOCTOR,
        )
        await self.report_repo.update_report(report.id, status=CASE_STATUS_AWAITING_DOCTOR)
        return self._build_case_detail(report, triage_case, result)

    async def start_review(self, report_id: UUID, doctor_name: str) -> CaseDetailResponse:
        detail = await self.get_case_detail(report_id)
        if detail.report_status not in {CASE_STATUS_AWAITING_DOCTOR, CASE_STATUS_UNDER_REVIEW}:
            raise BadRequestError("Case is not ready for doctor review")

        triage_case = await self.case_repo.update_case(
            report_id,
            report_status=CASE_STATUS_UNDER_REVIEW,
            doctor_name=doctor_name.strip(),
        )
        await self.report_repo.update_report(report_id, status=CASE_STATUS_UNDER_REVIEW)
        report = await self.report_repo.get_report(report_id)
        result = await self.report_repo.get_result(report_id)
        if not report:
            raise NotFoundError("Report not found")
        return self._build_case_detail(report, triage_case, result)

    async def finalize_case(
        self,
        report_id: UUID,
        *,
        doctor_name: str,
        decision: str,
        final_diagnosis: str | None,
        doctor_notes: str | None,
    ) -> CaseDetailResponse:
        report = await self.report_repo.get_report(report_id)
        if not report:
            raise NotFoundError("Report not found")

        triage_case = await self.case_repo.get_case(report_id)
        if not triage_case:
            raise NotFoundError("Triage case not found")

        result = await self.report_repo.get_result(report_id)
        if not result:
            raise BadRequestError("Case must finish AI analysis before finalization")

        if triage_case.report_status not in {CASE_STATUS_AWAITING_DOCTOR, CASE_STATUS_UNDER_REVIEW}:
            raise BadRequestError("Case is not in a finalizable state")

        triage_level = triage_case.triage_level or self._compute_triage_level(result)
        normalized_decision = decision.strip().upper()
        resolved_diagnosis = result.classification.get("disease", "unknown")
        if normalized_decision == "OVERRIDE":
            override_value = (final_diagnosis or "").strip()
            if not override_value:
                raise BadRequestError("Final diagnosis is required when overriding the AI prediction")
            resolved_diagnosis = override_value

        patient_explanation = self.guidance.generate_patient_explanation(
            patient_name=triage_case.patient_name,
            disease=resolved_diagnosis,
            findings_summary=result.findings.get("summary", ""),
            triage_level=triage_level,
        )
        lifestyle_guidance = self.guidance.generate_lifestyle_guidance(
            lifestyle_recommendations=result.lifestyle.get("recommendations", []),
            follow_up_recommendations=result.follow_up.get("recommendations", []),
        )

        finalized_at = datetime.now(timezone.utc)
        automation_payload = {
            "event": "case.finalized",
            "source": "radion-ai-backend",
            "version": "1.0",
            "case_id": str(report.id),
            "report_id": str(report.id),
            "patient_token": triage_case.patient_token,
            "to_email": triage_case.patient_email,
            "disease": resolved_diagnosis,
            "patient_explanation": {
                "text": patient_explanation,
            },
            "lifestyle_recommendations": lifestyle_guidance,
            "finalized_at": finalized_at.isoformat(),
        }
        automation_status = self.automation.trigger_case_finalized(automation_payload)

        triage_case = await self.case_repo.update_case(
            report.id,
            report_status=CASE_STATUS_FINALIZED,
            doctor_name=doctor_name.strip(),
            doctor_notes=doctor_notes,
            review_decision=normalized_decision,
            final_diagnosis=resolved_diagnosis,
            patient_explanation=patient_explanation,
            lifestyle_guidance=lifestyle_guidance,
            automation_status=automation_status,
            finalized_at=finalized_at,
            predicted_disease=result.classification.get("disease", "unknown"),
            confidence_score=float(result.classification.get("confidence", 0.0)),
            triage_level=triage_level,
        )
        await self.report_repo.update_report(report.id, status=CASE_STATUS_FINALIZED)

        return self._build_case_detail(report, triage_case, result)

    async def get_triage_result_summary(self, report_id: UUID) -> TriageResultSummaryResponse:
        report = await self.report_repo.get_report(report_id)
        if not report:
            raise NotFoundError("Report not found")

        detail = await self.get_case_detail(report_id)
        result = await self.report_repo.get_result(report_id)
        if (
            detail.report_status == CASE_STATUS_AI_ANALYZED
            and detail.predicted_disease
            and detail.confidence_score is not None
            and detail.triage_level
            and result is not None
        ):
            triage_case = await self.case_repo.update_case(report_id, report_status=CASE_STATUS_AWAITING_DOCTOR)
            await self.report_repo.update_report(report_id, status=CASE_STATUS_AWAITING_DOCTOR)
            detail = self._build_case_detail(report, triage_case, result)

        triage_result = await self.report_repo.get_triage_result(report_id)

        if not detail.analysis:
            raise BadRequestError("Case analysis is not available")

        if triage_result is None:
            triage_result = await self.report_repo.create_triage_result(
                report_id,
                disease_prediction=detail.predicted_disease or detail.analysis.classification.disease,
                confidence_score=detail.confidence_score or detail.analysis.classification.confidence,
                urgency_level=detail.triage_level or normalize_triage_level(detail.analysis.triage.urgency_label),
                explanation=self._build_triage_explanation(detail.analysis),
            )

        evidence_words = detail.analysis.explainability.top_keywords or detail.analysis.explainability.evidence
        return TriageResultSummaryResponse(
            report_id=report_id,
            disease_prediction=triage_result.disease_prediction,
            confidence_score=triage_result.confidence_score,
            urgency_level=triage_result.urgency_level,
            explanation=triage_result.explanation,
            evidence_words=evidence_words[:5],
            positive_findings=detail.analysis.findings.positive_findings[:8],
            negated_findings=detail.analysis.findings.negated_findings[:8],
            created_at=triage_result.created_at,
        )

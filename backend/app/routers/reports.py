from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_role
from app.models.user import User
from app.repositories.report_repo import ReportRepository
from app.schemas.report import (
    ReportDetailResponse,
    ReportProcessResponse,
    ReportUploadResponse,
)
from app.services.disease_trend_analysis import DiseaseTrendAnalysisService
from app.services.report_ingest import ingest_report
from app.services.report_pipeline import ReportPipelineService
from app.services.smart_critical_alerts import SmartCriticalAlertsService
from app.utils.errors import NotFoundError

router = APIRouter(prefix="/v1/reports", tags=["reports"])


async def _enrich_analysis_with_context(db: AsyncSession, analysis: ReportProcessResponse) -> ReportProcessResponse:
    trend_analysis = await DiseaseTrendAnalysisService(db).analyze(analysis.classification.disease)
    critical_alerts = SmartCriticalAlertsService().build(
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


def _analysis_payload(response: ReportProcessResponse) -> dict[str, object]:
    return {
        "findings": response.findings.model_dump(),
        "classification": response.classification.model_dump(),
        "triage": response.triage.model_dump(),
        "explainability": response.explainability.model_dump(),
        "inconsistencies": response.inconsistencies.model_dump(),
        "lifestyle": response.lifestyle.model_dump(),
        "follow_up": response.follow_up.model_dump(),
        "patient_explanation": response.patient_explanation.model_dump(),
        "trend_analysis": response.trend_analysis.model_dump(),
        "critical_alerts": response.critical_alerts.model_dump(),
        "notification": response.notification.model_dump(),
    }


@router.post("/upload", response_model=ReportUploadResponse)
async def upload_report(
    text: str | None = Form(default=None),
    file: UploadFile | None = File(default=None),
    _current_user: User = Depends(require_role("lab_technician")),
    db: AsyncSession = Depends(get_db),
):
    raw_text, source_type = await ingest_report(text, file)
    repo = ReportRepository(db)
    report = await repo.create_report(source_type=source_type, raw_text=raw_text)
    return ReportUploadResponse(report_id=report.id, source_type=report.source_type, created_at=report.created_at)


@router.post("/{report_id}/process", response_model=ReportProcessResponse)
async def process_report(
    report_id: UUID,
    _current_user: User = Depends(require_role("doctor", "lab_technician")),
    db: AsyncSession = Depends(get_db),
):
    repo = ReportRepository(db)
    report = await repo.get_report(report_id)
    if not report:
        raise NotFoundError("Report not found")

    pipeline = ReportPipelineService()
    response = await _enrich_analysis_with_context(db, pipeline.process(report_id, report.raw_text))
    payload = _analysis_payload(response)
    await repo.create_result(report_id, payload)
    return response


@router.get("/{report_id}", response_model=ReportDetailResponse)
async def get_report(
    report_id: UUID,
    _current_user: User = Depends(require_role("doctor", "lab_technician")),
    db: AsyncSession = Depends(get_db),
):
    repo = ReportRepository(db)
    report = await repo.get_report(report_id)
    if not report:
        raise NotFoundError("Report not found")
    result = await repo.get_result(report_id)
    return ReportDetailResponse(
        report_id=report.id,
        source_type=report.source_type,
        raw_text=report.raw_text,
        created_at=report.created_at,
        result=(
            ReportProcessResponse(
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
            if result
            else None
        ),
    )

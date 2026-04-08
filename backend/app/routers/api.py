from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, require_role
from app.core.database import get_db, get_session_factory
from app.models.db import Report, ReportResult
from app.models.user import User
from app.repositories.case_repo import CaseRepository
from app.repositories.report_repo import ReportRepository
from app.schemas.api import (
    AnalyzeReportRequest,
    AnalyzeReportResponse,
    DashboardStatsAPIResponse,
    NotifyPatientRequest,
    NotifyPatientResponse,
)
from app.schemas.case import (
    CaseDetailResponse,
    CaseUploadResponse,
    DoctorCasesResponse,
    FinalizeCaseRequest,
    StartReviewRequest,
    TriageQueueResponse,
)
from app.schemas.patient import PatientCreateResponse, PatientRegistrationRequest, PatientRegistrationResponse
from app.schemas.report import ReportProcessResponse, TriageResultSummaryResponse
from app.services.case_management import CASE_STATUS_AWAITING_DOCTOR, CaseManagementService
from app.services.disease_trend_analysis import DiseaseTrendAnalysisService
from app.services.dashboard import DashboardService
from app.services.notification import NotificationService
from app.services.report_pipeline import ReportPipelineService
from app.services.smart_critical_alerts import SmartCriticalAlertsService
from app.services.triage_service import RadiologyTriageService
from app.utils.errors import BadRequestError, NotFoundError

router = APIRouter(tags=["api"])
logger = logging.getLogger(__name__)


async def _analyze_case_in_background(report_id: UUID) -> None:
    session_factory = get_session_factory()
    async with session_factory() as db:
        try:
            await CaseManagementService(db).analyze_case(report_id)
        except Exception as exc:
            logger.exception("Background case analysis failed", exc_info=exc)


async def _create_patient_record(payload: PatientRegistrationRequest, db: AsyncSession):
    return await RadiologyTriageService(db).register_patient(payload)


async def _upload_case_record(
    *,
    background_tasks: BackgroundTasks,
    db: AsyncSession,
    patient_token: str,
    notes: str | None,
    report_file: UploadFile | None,
    xray_image: UploadFile | None,
    modality: str | None,
    ) -> CaseUploadResponse:
    return await RadiologyTriageService(db).upload_case(
        background_tasks=background_tasks,
        patient_token=patient_token,
        notes=notes,
        report_file=report_file,
        xray_image=xray_image,
        modality=modality,
        background_job=_analyze_case_in_background,
    )


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


@router.post("/upload-report", response_model=CaseUploadResponse)
async def upload_report(
    background_tasks: BackgroundTasks,
    patient_token: str = Form(...),
    notes: str | None = Form(default=None),
    report_file: UploadFile | None = File(default=None),
    xray_image: UploadFile | None = File(default=None),
    modality: str | None = Form(default=None),
    _current_user: User = Depends(require_role("lab_technician")),
    db: AsyncSession = Depends(get_db),
):
    return await _upload_case_record(
        background_tasks=background_tasks,
        db=db,
        patient_token=patient_token,
        notes=notes,
        report_file=report_file,
        xray_image=xray_image,
        modality=modality,
    )


@router.post("/patients/register", response_model=PatientRegistrationResponse)
async def register_patient(
    payload: PatientRegistrationRequest,
    _current_user: User = Depends(require_role("lab_technician")),
    db: AsyncSession = Depends(get_db),
):
    patient = await _create_patient_record(payload, db)
    return PatientRegistrationResponse(
        patient_id=patient.id,
        patient_token=patient.token,
        token_number=patient.token_number or patient.token,
        patient_name=patient.patient_name,
        name=patient.name or patient.patient_name,
        email=patient.email,
        age=patient.age,
        gender=patient.gender,
        patient_type=patient.patient_type,
        created_at=patient.created_at,
    )


@router.post("/patients/create", response_model=PatientCreateResponse)
async def create_patient(
    payload: PatientRegistrationRequest,
    _current_user: User = Depends(require_role("lab_technician")),
    db: AsyncSession = Depends(get_db),
):
    patient = await _create_patient_record(payload, db)
    return PatientCreateResponse(
        id=patient.id,
        patient_token=patient.token,
        token_number=patient.token_number or patient.token,
        patient_name=patient.patient_name,
        name=patient.name or patient.patient_name,
        email=patient.email,
        age=patient.age,
        gender=patient.gender,
        patient_type=patient.patient_type,
        created_at=patient.created_at,
    )


@router.get("/patients", response_model=list[PatientRegistrationResponse])
async def list_patients(
    _current_user: User = Depends(require_role("lab_technician", "doctor")),
    db: AsyncSession = Depends(get_db),
):
    patients = await RadiologyTriageService(db).list_patients()
    return [
        PatientRegistrationResponse(
            patient_id=patient.id,
            patient_token=patient.token,
            token_number=patient.token_number or patient.token,
            patient_name=patient.patient_name,
            name=patient.name or patient.patient_name,
            email=patient.email,
            age=patient.age,
            gender=patient.gender,
            patient_type=patient.patient_type,
            created_at=patient.created_at,
        )
        for patient in patients
    ]


@router.post("/reports/upload", response_model=CaseUploadResponse)
async def upload_report_contract(
    background_tasks: BackgroundTasks,
    patient_token: str = Form(...),
    notes: str | None = Form(default=None),
    report_file: UploadFile | None = File(default=None),
    report_pdf: UploadFile | None = File(default=None),
    xray_image: UploadFile | None = File(default=None),
    modality: str | None = Form(default=None),
    _current_user: User = Depends(require_role("lab_technician")),
    db: AsyncSession = Depends(get_db),
):
    return await _upload_case_record(
        background_tasks=background_tasks,
        db=db,
        patient_token=patient_token,
        notes=notes,
        report_file=report_file or report_pdf,
        xray_image=xray_image,
        modality=modality,
    )


@router.post("/analyze-report", response_model=AnalyzeReportResponse)
async def analyze_report(
    payload: AnalyzeReportRequest,
    _current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not payload.text and not payload.report_id:
        raise BadRequestError("Provide report_id or text to analyze.")

    repo = ReportRepository(db)
    if payload.report_id:
        report = await repo.get_report(payload.report_id)
        if not report:
            raise NotFoundError("Report not found")
        report_id = report.id
        case_repo = CaseRepository(db)
        triage_case = await case_repo.get_case(report_id)
        case_service = CaseManagementService(db)
        if triage_case:
            detail = await case_service.get_case_detail(report_id)
            if detail.analysis:
                return AnalyzeReportResponse(report=detail.analysis)

            detail = await case_service.analyze_case(report_id)
            if not detail.analysis:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Case analysis was not completed",
                )
            return AnalyzeReportResponse(report=detail.analysis)

        text = report.raw_text
    else:
        raw_text = (payload.text or "").strip()
        if not raw_text:
            raise BadRequestError("Provided text is empty.")
        report = await repo.create_report(source_type="text", raw_text=raw_text)
        text = report.raw_text
        report_id = report.id

    pipeline = ReportPipelineService()
    analysis = await _enrich_analysis_with_context(db, pipeline.process(report_id, text))
    payload_result = _analysis_payload(analysis)
    await repo.create_result(report_id, payload_result)

    return AnalyzeReportResponse(report=analysis)


@router.get("/triage-cases", response_model=TriageQueueResponse)
async def triage_cases(
    status_filter: str | None = Query(default=None, alias="status"),
    patient_token: str | None = Query(default=None, alias="patientToken"),
    _current_user: User = Depends(require_role("doctor")),
    db: AsyncSession = Depends(get_db),
):
    cases = await CaseManagementService(db).list_triage_cases(
        report_status=status_filter.strip().upper() if status_filter else None,
        patient_token=patient_token.strip() if patient_token else None,
    )
    return TriageQueueResponse(cases=cases)


@router.get("/doctor/cases", response_model=DoctorCasesResponse)
async def doctor_cases(
    status_filter: str | None = Query(default=CASE_STATUS_AWAITING_DOCTOR, alias="status"),
    _current_user: User = Depends(require_role("doctor")),
    db: AsyncSession = Depends(get_db),
):
    return await RadiologyTriageService(db).get_doctor_cases(
        report_status=status_filter.strip().upper() if status_filter else CASE_STATUS_AWAITING_DOCTOR
    )


@router.get("/cases/{case_id}", response_model=CaseDetailResponse)
async def get_case(
    case_id: UUID,
    _current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await CaseManagementService(db).get_case_detail(case_id)


@router.get("/triage/result/{report_id}", response_model=TriageResultSummaryResponse)
async def get_triage_result(
    report_id: UUID,
    _current_user: User = Depends(require_role("doctor", "lab_technician")),
    db: AsyncSession = Depends(get_db),
):
    return await RadiologyTriageService(db).get_triage_result(report_id)


@router.post("/cases/{case_id}/review", response_model=CaseDetailResponse)
async def start_case_review(
    case_id: UUID,
    payload: StartReviewRequest,
    _current_user: User = Depends(require_role("doctor")),
    db: AsyncSession = Depends(get_db),
):
    return await CaseManagementService(db).start_review(case_id, doctor_name=payload.doctor_name)


@router.post("/cases/{case_id}/finalize", response_model=CaseDetailResponse)
async def finalize_case(
    case_id: UUID,
    payload: FinalizeCaseRequest,
    _current_user: User = Depends(require_role("doctor")),
    db: AsyncSession = Depends(get_db),
):
    return await CaseManagementService(db).finalize_case(
        case_id,
        doctor_name=payload.doctor_name,
        decision=payload.decision,
        final_diagnosis=payload.final_diagnosis,
        doctor_notes=payload.doctor_notes,
    )


@router.get("/legacy-triage-cases")
async def legacy_triage_cases(
    _current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await db.execute(
            select(ReportResult, Report)
            .join(Report, ReportResult.report_id == Report.id)
            .order_by(ReportResult.created_at.desc())
        )
        rows = result.all()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load triage cases",
        ) from exc
    return {"count": len(rows)}


@router.get("/dashboard-stats", response_model=DashboardStatsAPIResponse)
async def dashboard_stats(
    _current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stats = await DashboardService(db).get_stats()
    return DashboardStatsAPIResponse(stats=stats, generated_at=datetime.now(timezone.utc))


@router.post("/notify-patient", response_model=NotifyPatientResponse)
async def notify_patient(
    payload: NotifyPatientRequest,
    _current_user: User = Depends(require_role("doctor")),
    db: AsyncSession = Depends(get_db),
):
    repo = ReportRepository(db)
    report = await repo.get_report(payload.report_id)
    if not report:
        raise NotFoundError("Report not found")

    result = await repo.get_result(payload.report_id)
    if not result:
        pipeline = ReportPipelineService()
        analysis = await _enrich_analysis_with_context(db, pipeline.process(report.id, report.raw_text))
        payload_result = _analysis_payload(analysis)
        await repo.create_result(report.id, payload_result)
        triage_data = analysis.triage
    else:
        triage_data = ReportProcessResponse(
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
        ).triage

    notification_service = NotificationService()
    notification = notification_service.trigger(triage_data)

    if payload.channels:
        notification.channels = payload.channels

    return NotifyPatientResponse(report_id=report.id, notification=notification)

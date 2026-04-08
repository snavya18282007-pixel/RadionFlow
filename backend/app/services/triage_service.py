from __future__ import annotations

from uuid import UUID

from fastapi import BackgroundTasks, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.case_repo import CaseRepository
from app.repositories.patient_repo import PatientRepository
from app.repositories.report_repo import ReportRepository
from app.schemas.case import CaseUploadResponse, DoctorCasesResponse
from app.schemas.patient import PatientRegistrationRequest
from app.schemas.report import TriageResultSummaryResponse
from app.services.case_management import CASE_STATUS_AWAITING_DOCTOR, CaseManagementService
from app.services.report_ingest import ingest_report
from app.services.token_service import TokenService
from app.utils.errors import BadRequestError, NotFoundError
from app.utils.text import normalize_text


class RadiologyTriageService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.patient_repo = PatientRepository(db)
        self.report_repo = ReportRepository(db)
        self.case_repo = CaseRepository(db)
        self.case_management = CaseManagementService(db)
        self.token_service = TokenService(db)

    async def register_patient(self, payload: PatientRegistrationRequest):
        token = await self.token_service.next_patient_token()
        return await self.patient_repo.create_patient(
            token=token,
            patient_name=payload.patient_name or payload.name or "",
            email=str(payload.email),
            age=payload.age,
            gender=payload.gender,
            patient_type=payload.patient_type,
        )

    async def list_patients(self):
        return await self.patient_repo.list_patients()

    async def upload_case(
        self,
        *,
        background_tasks: BackgroundTasks,
        patient_token: str,
        notes: str | None,
        report_file: UploadFile | None,
        xray_image: UploadFile | None,
        modality: str | None,
        background_job,
    ) -> CaseUploadResponse:
        patient = await self.patient_repo.get_patient(patient_token.strip())
        if not patient:
            raise NotFoundError("Patient token not found")

        if xray_image and (not xray_image.content_type or not xray_image.content_type.startswith("image/")):
            raise BadRequestError("Unsupported X-ray image type")

        raw_text, source_type = await self._resolve_report_payload(notes=notes, report_file=report_file)

        resolved_modality = (modality or ("XRAY" if xray_image else "REPORT")).strip().upper()
        file_url = report_file.filename if report_file else (xray_image.filename if xray_image else None)

        report = await self.report_repo.create_report(
            source_type=source_type,
            raw_text=raw_text,
            patient_id=patient.id,
            patient_token=patient.token,
            file_url=file_url,
            modality=resolved_modality,
            status="UPLOADED",
        )
        triage_case = await self.case_repo.create_case(
            report_id=report.id,
            patient_name=patient.patient_name,
            patient_token=patient.token,
            patient_email=patient.email,
            patient_age=patient.age,
            patient_gender=patient.gender,
            patient_type=patient.patient_type,
            upload_metadata={
                "notes": notes,
                "report_file_name": report_file.filename if report_file else None,
                "xray_file_name": xray_image.filename if xray_image else None,
                "xray_content_type": xray_image.content_type if xray_image else None,
                "modality": resolved_modality,
            },
        )
        background_tasks.add_task(background_job, report.id)

        return CaseUploadResponse(
            case_id=report.id,
            report_id=report.id,
            patient_token=triage_case.patient_token,
            patient_name=triage_case.patient_name,
            report_status=triage_case.report_status,
            created_at=triage_case.created_at,
            disease_prediction=None,
            confidence_score=None,
            urgency_level=None,
            explanation=None,
        )

    async def get_doctor_cases(self, report_status: str | None = CASE_STATUS_AWAITING_DOCTOR) -> DoctorCasesResponse:
        grouped = await self.case_management.group_doctor_cases(report_status=report_status)
        return DoctorCasesResponse(**grouped)

    async def get_triage_result(self, report_id: UUID) -> TriageResultSummaryResponse:
        return await self.case_management.get_triage_result_summary(report_id)

    async def _resolve_report_payload(self, *, notes: str | None, report_file: UploadFile | None) -> tuple[str, str]:
        if report_file and report_file.content_type in {"image/png", "image/jpeg", "image/jpg"}:
            if not notes or not notes.strip():
                raise BadRequestError("Provide notes when uploading PNG or JPG reports because OCR is not configured.")
            return normalize_text(notes), "image"

        report_text_input = notes if not report_file else None
        raw_text, source_type = await ingest_report(report_text_input, report_file)
        if notes and report_file:
            raw_text = normalize_text(f"{raw_text}\n\nClinical notes: {notes}")
        return raw_text, source_type

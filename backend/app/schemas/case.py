from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.report import ReportProcessResponse


class CaseUploadResponse(BaseModel):
    case_id: UUID
    report_id: UUID
    patient_token: str
    patient_name: str
    report_status: str
    created_at: datetime
    disease_prediction: str | None = None
    confidence_score: float | None = None
    urgency_level: str | None = None
    explanation: str | None = None


class TriageQueueCase(BaseModel):
    case_id: UUID
    patient_token: str
    patient_name: str
    predicted_disease: str
    confidence_score: float
    triage_level: str
    report_status: str
    created_at: datetime


class TriageQueueResponse(BaseModel):
    cases: list[TriageQueueCase]


class DoctorCasesResponse(BaseModel):
    critical: list[TriageQueueCase] = Field(default_factory=list)
    high: list[TriageQueueCase] = Field(default_factory=list)
    medium: list[TriageQueueCase] = Field(default_factory=list)
    low: list[TriageQueueCase] = Field(default_factory=list)


class StartReviewRequest(BaseModel):
    doctor_name: str = Field(min_length=1)


class FinalizeCaseRequest(BaseModel):
    doctor_name: str = Field(min_length=1)
    decision: str = Field(pattern="^(APPROVE|OVERRIDE)$")
    final_diagnosis: str | None = None
    doctor_notes: str | None = None


class CaseDetailResponse(BaseModel):
    case_id: UUID
    patient_token: str
    patient_name: str
    patient_email: str | None = None
    patient_age: int | None = None
    patient_gender: str | None = None
    patient_type: str | None = None
    report_status: str
    triage_level: str | None = None
    predicted_disease: str | None = None
    confidence_score: float | None = None
    doctor_name: str | None = None
    doctor_notes: str | None = None
    review_decision: str | None = None
    final_diagnosis: str | None = None
    patient_explanation: str | None = None
    lifestyle_guidance: list[str] = Field(default_factory=list)
    upload_metadata: dict[str, Any] = Field(default_factory=dict)
    automation_status: dict[str, Any] = Field(default_factory=dict)
    source_type: str
    raw_text: str
    created_at: datetime
    finalized_at: datetime | None = None
    analysis: ReportProcessResponse | None = None

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.dashboard import DashboardStatsResponse
from app.schemas.report import NotificationResponse, ReportProcessResponse


class UploadReportResponse(BaseModel):
    report_id: UUID
    source_type: str
    created_at: datetime


class AnalyzeReportRequest(BaseModel):
    report_id: UUID | None = None
    text: str | None = Field(default=None, min_length=1)


class AnalyzeReportResponse(BaseModel):
    report: ReportProcessResponse


class TriageCaseItem(BaseModel):
    report_id: UUID
    disease: str
    confidence: float
    urgency_category: str
    priority_score: float
    recommended_review_minutes: int
    created_at: datetime


class TriageQueueResponse(BaseModel):
    cases: list[TriageCaseItem]


class NotifyPatientRequest(BaseModel):
    report_id: UUID
    channels: list[str] | None = None


class NotifyPatientResponse(BaseModel):
    report_id: UUID
    notification: NotificationResponse


class DashboardStatsAPIResponse(BaseModel):
    stats: DashboardStatsResponse
    generated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)

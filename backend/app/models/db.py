from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), index=True, nullable=True)
    patient_token: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)
    file_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    modality: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="UPLOADED")
    source_type: Mapped[str] = mapped_column(String(20))
    raw_text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ReportResult(Base):
    __tablename__ = "report_results"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), index=True)
    findings: Mapped[dict] = mapped_column(JSON)
    classification: Mapped[dict] = mapped_column(JSON)
    triage: Mapped[dict] = mapped_column(JSON)
    explainability: Mapped[dict] = mapped_column(JSON)
    inconsistencies: Mapped[dict] = mapped_column(JSON)
    lifestyle: Mapped[dict] = mapped_column(JSON)
    follow_up: Mapped[dict] = mapped_column(JSON)
    patient_explanation: Mapped[dict] = mapped_column(JSON, default=dict)
    trend_analysis: Mapped[dict] = mapped_column(JSON, default=dict)
    critical_alerts: Mapped[dict] = mapped_column(JSON, default=dict)
    notification: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), unique=True, index=True, default=uuid.uuid4, nullable=True)
    token: Mapped[str] = mapped_column(String(32), primary_key=True)
    token_number: Mapped[str | None] = mapped_column(String(32), unique=True, index=True, nullable=True)
    patient_name: Mapped[str] = mapped_column(String(120))
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    age: Mapped[int] = mapped_column()
    gender: Mapped[str] = mapped_column(String(32))
    patient_type: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class TriageResult(Base):
    __tablename__ = "triage_results"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("reports.id", ondelete="CASCADE"),
        index=True,
    )
    disease_prediction: Mapped[str] = mapped_column(String(120))
    confidence_score: Mapped[float] = mapped_column(Float)
    urgency_level: Mapped[str] = mapped_column(String(16), index=True)
    explanation: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class TriageCase(Base):
    __tablename__ = "triage_cases"

    report_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("reports.id", ondelete="CASCADE"),
        primary_key=True,
    )
    patient_token: Mapped[str] = mapped_column(String(32), index=True)
    patient_name: Mapped[str] = mapped_column(String(120))
    patient_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    patient_age: Mapped[int | None] = mapped_column(nullable=True)
    patient_gender: Mapped[str | None] = mapped_column(String(32), nullable=True)
    patient_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    report_status: Mapped[str] = mapped_column(String(32), index=True, default="UPLOADED")
    predicted_disease: Mapped[str | None] = mapped_column(String(120), nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    triage_level: Mapped[str | None] = mapped_column(String(16), index=True, nullable=True)
    doctor_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    doctor_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_decision: Mapped[str | None] = mapped_column(String(16), nullable=True)
    final_diagnosis: Mapped[str | None] = mapped_column(String(120), nullable=True)
    patient_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    lifestyle_guidance: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    upload_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    automation_status: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

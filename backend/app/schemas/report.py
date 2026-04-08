from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ReportUploadRequest(BaseModel):
    text: str | None = Field(default=None, description="Raw report text")


class ReportUploadResponse(BaseModel):
    report_id: UUID
    source_type: str
    created_at: datetime


class FindingItem(BaseModel):
    label: str
    confidence: float
    evidence: str | None = None


class FindingsResponse(BaseModel):
    entities: list[FindingItem]
    summary: str
    findings: list[str] = Field(default_factory=list)
    body_region: str = "chest"
    severity_terms: list[str] = Field(default_factory=list)
    positive_findings: list[str] = Field(default_factory=list)
    negated_findings: list[str] = Field(default_factory=list)


class ClassificationResponse(BaseModel):
    disease: str
    confidence: float
    probabilities: dict[str, float]
    model_source: str | None = None


class TriageResponse(BaseModel):
    urgency_score: float = Field(ge=0.0, le=1.0)
    urgency_label: str
    rationale: str


class ExplainabilityResponse(BaseModel):
    evidence: list[str]
    top_keywords: list[str] = Field(default_factory=list)
    positive_findings: list[str] = Field(default_factory=list)
    negated_findings: list[str] = Field(default_factory=list)
    model_insights: dict[str, Any]
    model_config = {"protected_namespaces": ()}


class TriageResultSummaryResponse(BaseModel):
    report_id: UUID
    disease_prediction: str
    confidence_score: float
    urgency_level: str
    explanation: str
    evidence_words: list[str] = Field(default_factory=list)
    positive_findings: list[str] = Field(default_factory=list)
    negated_findings: list[str] = Field(default_factory=list)
    created_at: datetime


class InconsistencyResponse(BaseModel):
    detected: bool
    reason: str | None = None
    details: list[str]


class LifestyleRecommendation(BaseModel):
    recommendations: list[str]


class FollowUpRecommendation(BaseModel):
    recommendations: list[str]
    timeframe_days: int


class PatientExplanationResponse(BaseModel):
    summary: str
    key_points: list[str]


class TrendAnalysisResponse(BaseModel):
    disease: str
    recent_case_count: int
    previous_case_count: int
    critical_case_count: int
    window_days: int
    trend_direction: str
    summary: str


class CriticalAlertItem(BaseModel):
    severity: str
    title: str
    message: str


class CriticalAlertsResponse(BaseModel):
    triggered: bool
    alerts: list[CriticalAlertItem]


class NotificationResponse(BaseModel):
    triggered: bool
    channels: list[str]
    message: str


class ReportProcessResponse(BaseModel):
    report_id: UUID
    findings: FindingsResponse
    classification: ClassificationResponse
    triage: TriageResponse
    explainability: ExplainabilityResponse
    inconsistencies: InconsistencyResponse
    lifestyle: LifestyleRecommendation
    follow_up: FollowUpRecommendation
    patient_explanation: PatientExplanationResponse
    trend_analysis: TrendAnalysisResponse
    critical_alerts: CriticalAlertsResponse
    notification: NotificationResponse
    processed_at: datetime

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "report_id": "b3a0b1d0-3a0e-4a72-99b9-0f1b62b15a0a",
                    "findings": {
                        "entities": [
                            {"label": "pulmonary nodule", "confidence": 0.91, "evidence": "2 cm RUL nodule"}
                        ],
                        "summary": "Solitary right upper lobe nodule with mild atelectasis."
                    },
                    "classification": {
                        "disease": "lung nodule",
                        "confidence": 0.87,
                        "probabilities": {"lung nodule": 0.87, "pneumonia": 0.07, "normal": 0.06}
                    },
                    "triage": {
                        "urgency_score": 0.78,
                        "urgency_label": "urgent",
                        "rationale": "Suspicious nodule size warrants short-term follow up."
                    },
                    "explainability": {
                        "evidence": ["2 cm RUL nodule", "spiculated margins"],
                        "model_insights": {"top_tokens": ["nodule", "spiculated", "RUL"]}
                    },
                    "inconsistencies": {
                        "detected": False,
                        "reason": None,
                        "details": []
                    },
                    "lifestyle": {
                        "recommendations": ["Smoking cessation support", "Follow low-dose CT screening guidance"]
                    },
                    "follow_up": {
                        "recommendations": ["Repeat chest CT in 3 months", "Pulmonology referral"],
                        "timeframe_days": 90
                    },
                    "notification": {
                        "triggered": True,
                        "channels": ["email", "sms"],
                        "message": "Urgent finding identified. Please schedule follow-up."
                    },
                    "processed_at": "2026-03-13T10:45:00Z"
                }
            ]
        }
    }


class ReportDetailResponse(BaseModel):
    report_id: UUID
    source_type: str
    raw_text: str
    created_at: datetime
    result: ReportProcessResponse | None

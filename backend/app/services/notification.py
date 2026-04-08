from __future__ import annotations

from app.schemas.report import NotificationResponse, TriageResponse


class NotificationService:
    def trigger(self, triage: TriageResponse) -> NotificationResponse:
        if triage.urgency_score >= 0.6:
            return NotificationResponse(
                triggered=True,
                channels=["email", "sms"],
                message="Urgent finding identified. Please schedule follow-up.",
            )
        return NotificationResponse(triggered=False, channels=[], message="No urgent notification required.")

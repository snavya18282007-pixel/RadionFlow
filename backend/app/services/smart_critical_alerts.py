from __future__ import annotations

from app.schemas.report import CriticalAlertItem, CriticalAlertsResponse, InconsistencyResponse, TrendAnalysisResponse


class SmartCriticalAlertsService:
    def build(
        self,
        *,
        disease: str,
        findings: list[str],
        severity_terms: list[str],
        urgency_level: str,
        confidence: float,
        inconsistencies: InconsistencyResponse,
        trend_analysis: TrendAnalysisResponse,
    ) -> CriticalAlertsResponse:
        alerts: list[CriticalAlertItem] = []
        normalized_findings = {item.lower() for item in findings}
        normalized_severity = {item.lower() for item in severity_terms}

        if urgency_level.upper() == "CRITICAL":
            alerts.append(
                CriticalAlertItem(
                    severity="critical",
                    title="Immediate radiologist review",
                    message=f"{disease} has been triaged as critical and should be reviewed without delay.",
                )
            )

        if "pneumothorax" in normalized_findings:
            alerts.append(
                CriticalAlertItem(
                    severity="critical",
                    title="Possible pneumothorax detected",
                    message="Pneumothorax language was found in the report findings and requires urgent confirmation.",
                )
            )

        if {"mass", "nodule"} & normalized_findings and {"suspicious", "spiculated"} & normalized_severity:
            alerts.append(
                CriticalAlertItem(
                    severity="high",
                    title="Suspicious mass features",
                    message="Mass-like findings with suspicious descriptors may represent malignancy and warrant rapid review.",
                )
            )

        if inconsistencies.detected:
            alerts.append(
                CriticalAlertItem(
                    severity="high",
                    title="Report inconsistency detected",
                    message=inconsistencies.reason or "The report contains internally conflicting statements that should be checked by a doctor.",
                )
            )

        if trend_analysis.trend_direction == "increasing" and trend_analysis.recent_case_count >= 3:
            alerts.append(
                CriticalAlertItem(
                    severity="medium",
                    title="Rising disease trend",
                    message=trend_analysis.summary,
                )
            )

        if urgency_level.upper() in {"HIGH", "CRITICAL"} and confidence < 0.55:
            alerts.append(
                CriticalAlertItem(
                    severity="medium",
                    title="Escalated with lower model certainty",
                    message="The case is prioritized for review, but model confidence is modest and clinician confirmation is especially important.",
                )
            )

        return CriticalAlertsResponse(triggered=bool(alerts), alerts=alerts)

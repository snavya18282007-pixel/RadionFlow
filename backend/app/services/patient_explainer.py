from __future__ import annotations

from app.schemas.report import PatientExplanationResponse


class PatientExplainerService:
    def generate(
        self,
        *,
        disease: str,
        findings: list[str],
        body_region: str,
        urgency_level: str,
    ) -> PatientExplanationResponse:
        readable_disease = disease if disease and disease.lower() != "unknown" else "an imaging abnormality"
        readable_findings = ", ".join(findings[:3]) if findings else "no definite abnormal findings"

        summary = (
            f"The AI review suggests {readable_disease} involving the {body_region}. "
            f"Current triage priority is {urgency_level.lower()}."
        )
        key_points = [
            f"Detected findings: {readable_findings}.",
            "This result is an AI-generated triage assessment and still needs clinician review.",
        ]
        if urgency_level.upper() in {"HIGH", "CRITICAL"}:
            key_points.append("A doctor should review this study promptly.")
        else:
            key_points.append("The case can remain in the standard clinical review queue.")

        return PatientExplanationResponse(summary=summary, key_points=key_points)

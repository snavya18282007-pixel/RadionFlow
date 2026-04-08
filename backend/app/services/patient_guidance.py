from __future__ import annotations


class PatientGuidanceService:
    def generate_patient_explanation(
        self,
        *,
        patient_name: str,
        disease: str,
        findings_summary: str,
        triage_level: str,
    ) -> str:
        condition = disease if disease and disease.lower() != "unknown" else "an abnormal imaging finding"
        summary = findings_summary.strip() or "the imaging findings need medical review"
        return (
            f"{patient_name}, your scan suggests {condition}. "
            f"The AI system marked this case as {triage_level.lower()} priority because {summary}. "
            "This is not the final diagnosis. A doctor has reviewed the case and will explain the confirmed result and next steps."
        )

    def generate_lifestyle_guidance(
        self,
        *,
        lifestyle_recommendations: list[str],
        follow_up_recommendations: list[str],
    ) -> list[str]:
        guidance = [item.strip() for item in lifestyle_recommendations if item and item.strip()]
        guidance.extend(item.strip() for item in follow_up_recommendations if item and item.strip())
        guidance.append("Seek urgent care immediately if symptoms worsen before your follow-up.")
        return list(dict.fromkeys(guidance))

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LifestyleRecommendation:
    disease: str
    recommendations: list[str]
    disclaimer: str

    def to_notification_payload(self) -> dict:
        return {
            "disease": self.disease,
            "recommendations": self.recommendations,
            "disclaimer": self.disclaimer,
        }


class LifestyleRecommendationEngine:
    """Rule-based, patient-friendly lifestyle guidance generator."""

    _guidance_map: dict[str, list[str]] = {
        "cardiomegaly": [
            "Reduce sodium intake.",
            "Monitor blood pressure regularly.",
            "Keep regular cardiology checkups.",
            "Stay active with gentle, doctor-approved exercise.",
        ],
        "pneumonia": [
            "Rest and allow time to recover.",
            "Drink plenty of fluids.",
            "Avoid smoking and secondhand smoke.",
            "Follow prescribed medications as directed.",
        ],
        "pleural effusion": [
            "Avoid smoking and secondhand smoke.",
            "Keep follow-up appointments for repeat imaging.",
            "Report worsening shortness of breath promptly.",
        ],
        "pulmonary edema": [
            "Limit salt and fluid intake if advised.",
            "Monitor weight for sudden changes.",
            "Take medications exactly as prescribed.",
        ],
        "pneumothorax": [
            "Avoid strenuous activity until cleared by a clinician.",
            "Do not smoke or vape.",
            "Seek urgent care if breathing worsens.",
        ],
        "fracture": [
            "Follow activity restrictions.",
            "Ensure adequate calcium and vitamin D intake.",
            "Keep follow-up imaging appointments.",
        ],
        "normal": [
            "Maintain a healthy, balanced diet.",
            "Stay active with regular exercise.",
            "Keep routine checkups as advised.",
        ],
    }

    _default_guidance = [
        "Maintain a balanced diet.",
        "Stay hydrated.",
        "Avoid smoking and secondhand smoke.",
        "Follow up with your clinician as advised.",
    ]

    _disclaimer = (
        "These tips are general information and not a substitute for professional medical advice."
    )

    def recommend(self, disease: str) -> LifestyleRecommendation:
        key = disease.strip().lower()
        recs = self._guidance_map.get(key, self._default_guidance)
        return LifestyleRecommendation(disease=disease, recommendations=recs, disclaimer=self._disclaimer)

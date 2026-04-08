from __future__ import annotations

from app.schemas.report import FollowUpRecommendation


class FollowUpService:
    def recommend(self, disease: str) -> FollowUpRecommendation:
        disease_lower = disease.lower()
        if "fracture" in disease_lower:
            return FollowUpRecommendation(
                recommendations=["Orthopedics consultation", "Repeat imaging in 7-14 days"],
                timeframe_days=14,
            )
        if "tuberculosis" in disease_lower:
            return FollowUpRecommendation(
                recommendations=["Pulmonology or infectious disease referral", "Microbiology confirmation and isolation review"],
                timeframe_days=3,
            )
        if "pneumonia" in disease_lower:
            return FollowUpRecommendation(
                recommendations=["Clinical reassessment", "Repeat chest X-ray"],
                timeframe_days=30,
            )
        if "pleural effusion" in disease_lower:
            return FollowUpRecommendation(
                recommendations=["Ultrasound correlation if needed", "Clinical review for drainage decision"],
                timeframe_days=7,
            )
        if "mass" in disease_lower or "cancer" in disease_lower:
            return FollowUpRecommendation(
                recommendations=["Urgent chest CT or oncology pathway referral", "Tissue diagnosis planning"],
                timeframe_days=3,
            )
        if "nodule" in disease_lower:
            return FollowUpRecommendation(
                recommendations=["Pulmonology referral", "Repeat chest CT"],
                timeframe_days=90,
            )
        return FollowUpRecommendation(recommendations=["Routine follow-up"], timeframe_days=180)

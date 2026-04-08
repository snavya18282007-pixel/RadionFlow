from __future__ import annotations

from app.schemas.report import LifestyleRecommendation
from app.services.lifestyle_engine import LifestyleRecommendationEngine


class LifestyleService:
    def __init__(self) -> None:
        self.engine = LifestyleRecommendationEngine()

    def recommend(self, disease: str) -> LifestyleRecommendation:
        recs = self.engine.recommend(disease)
        return LifestyleRecommendation(recommendations=recs.recommendations)

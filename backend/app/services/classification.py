from __future__ import annotations

from app.schemas.report import ClassificationResponse
from app.services.ai_model_service import AIModelService
from app.services.disease_classifier import DiseaseClassifier


class DiseaseClassificationService:
    def __init__(self, model_service: AIModelService) -> None:
        self.classifier = DiseaseClassifier()

    def classify(self, text: str, findings: list[str] | None = None) -> ClassificationResponse:
        prediction = self.classifier.predict_disease(findings or [], text)
        return ClassificationResponse(
            disease=prediction.prediction,
            confidence=prediction.confidence,
            probabilities=prediction.probabilities,
            model_source=prediction.model_source,
        )

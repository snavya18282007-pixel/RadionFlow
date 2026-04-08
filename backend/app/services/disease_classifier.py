from __future__ import annotations

from dataclasses import dataclass

from app.services.radiology_classifier import RadiologyClassifierService, get_radiology_classifier


CANONICAL_LABELS = {
    "normal": "Normal",
    "pneumonia": "Pneumonia",
    "tuberculosis": "Tuberculosis",
    "pleural_effusion": "Pleural Effusion",
    "lung_cancer": "Lung Mass",
    "lung_mass": "Lung Mass",
    "fracture": "Fracture",
    "cardiomegaly": "Cardiomegaly",
    "other_lung_abnormality": "Other lung abnormality",
}


@dataclass(frozen=True)
class DiseasePredictionResult:
    prediction: str
    confidence: float
    probabilities: dict[str, float]
    evidence_words: list[str]
    model_source: str

    def to_dict(self) -> dict[str, object]:
        return {
            "prediction": self.prediction,
            "confidence": self.confidence,
            "probabilities": self.probabilities,
            "evidence_words": self.evidence_words,
            "model_source": self.model_source,
        }


def _unique_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _normalize_label(label: str | None) -> str:
    if not label:
        return "other_lung_abnormality"
    normalized = label.strip().lower().replace("-", "_").replace(" ", "_")
    alias_map = {
        "tb": "tuberculosis",
        "pleural_effusion": "pleural_effusion",
        "lung_cancer": "lung_cancer",
        "other_lung_abnormality": "other_lung_abnormality",
        "lung_mass": "lung_mass",
    }
    return alias_map.get(normalized, normalized)


def _display_label(label: str | None) -> str:
    return CANONICAL_LABELS.get(_normalize_label(label), (label or "Other lung abnormality").replace("_", " ").title())


class DiseaseClassifier:
    def __init__(self, classifier: RadiologyClassifierService | None = None) -> None:
        self.classifier = classifier or get_radiology_classifier()

    def predict_disease(self, findings: list[str], report_text: str) -> DiseasePredictionResult:
        normalized_findings = {_normalize_label(finding) for finding in findings}
        heuristic = self._heuristic_prediction(normalized_findings, report_text)
        model_prediction = self.classifier.predict(report_text)

        model_label = _normalize_label(model_prediction.normalized_label or model_prediction.disease)
        model_confidence = model_prediction.confidence
        selected_label = model_label
        selected_confidence = model_confidence
        selected_source = model_prediction.model_source

        if heuristic:
            heuristic_label, heuristic_confidence = heuristic
            if heuristic_label == model_label:
                selected_confidence = max(model_confidence, heuristic_confidence)
                selected_source = f"{model_prediction.model_source}+heuristic"
            elif heuristic_confidence >= model_confidence + 0.08 or heuristic_label in {"tuberculosis", "fracture", "lung_mass"}:
                selected_label = heuristic_label
                selected_confidence = max(heuristic_confidence, model_confidence if model_label == heuristic_label else 0.0)
                selected_source = f"{model_prediction.model_source}+heuristic-override"

        if not findings and selected_label != "normal":
            selected_label = "normal"
            selected_confidence = max(selected_confidence, 0.96)
            selected_source = "negation-aware-normal"

        probabilities = {
            _display_label(label): score for label, score in model_prediction.probabilities.items()
        }
        probabilities[_display_label(selected_label)] = round(max(probabilities.get(_display_label(selected_label), 0.0), selected_confidence), 4)

        evidence_words = _unique_preserve_order(model_prediction.top_keywords + [_display_label(item) for item in findings])[:5]

        return DiseasePredictionResult(
            prediction=_display_label(selected_label),
            confidence=round(selected_confidence, 4),
            probabilities=probabilities,
            evidence_words=evidence_words,
            model_source=selected_source,
        )

    def _heuristic_prediction(self, findings: set[str], report_text: str) -> tuple[str, float] | None:
        text = report_text.lower()
        if not findings and not text.strip():
            return "normal", 0.99

        if "tuberculosis" in findings or "tuberculosis" in text or " cavitary " in f" {text} ":
            return "tuberculosis", 0.92
        if "fracture" in findings:
            return "fracture", 0.9
        if "pleural_effusion" in findings:
            return "pleural_effusion", 0.85
        if {"pneumonia", "consolidation", "opacity"} & findings:
            return "pneumonia", 0.86
        if {"mass", "nodule"} & findings or "suspicious for malignancy" in text or "spiculated" in text:
            return "lung_mass", 0.89
        if "cardiomegaly" in findings:
            return "cardiomegaly", 0.82
        if not findings:
            return "normal", 0.96
        return None

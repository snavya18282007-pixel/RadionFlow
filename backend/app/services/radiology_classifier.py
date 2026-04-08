from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
APP_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = APP_ROOT / "models" / "radiology_classifier.pkl"
LEGACY_MODEL_PATH = PROJECT_ROOT / "models" / "radiology_classifier.pkl"

MODEL_STOPWORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "be",
    "because",
    "but",
    "by",
    "for",
    "from",
    "if",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "to",
    "up",
    "with",
    "within",
    "study",
    "views",
    "view",
    "exam",
    "examination",
    "film",
    "films",
    "comparison",
    "findings",
    "impression",
    "history",
    "portable",
    "pa",
    "ap",
    "lateral",
    "single",
    "two",
    "one",
    "xxxx",
}

LABEL_DISPLAY_NAMES = {
    "normal": "Normal",
    "cardiomegaly": "Cardiomegaly",
    "pleural_effusion": "Pleural Effusion",
    "pneumonia": "Pneumonia",
    "tuberculosis": "Tuberculosis",
    "lung_cancer": "Lung Cancer",
    "other_lung_abnormality": "Other lung abnormality",
}

LABEL_ORDER = (
    "tuberculosis",
    "lung_cancer",
    "pneumonia",
    "pleural_effusion",
    "cardiomegaly",
    "normal",
    "other_lung_abnormality",
)

NEGATION_PATTERN = re.compile(
    r"(?:no|without|negative for|no evidence of|no radiographic evidence of|free of|unlikely|exclude|excluded|rule out|r/o)",
    re.IGNORECASE,
)

RUNTIME_RULES: dict[str, tuple[str, ...]] = {
    "tuberculosis": (
        r"\bactive tuberculosis\b",
        r"\bconsistent with tuberculosis\b",
        r"\bcompatible with tuberculosis\b",
        r"\bpossibility of tuberculosis\b",
        r"\bprior tb\b",
        r"\bprior tuberculosis\b",
        r"\bcavitary lesion\b",
        r"\bcavitary opacity\b",
        r"\bfibrocavitary\b",
        r"\bapical pleural thickening\b",
        r"\bupper lobe infiltrate\b",
        r"\bgranulomatous disease\b",
    ),
    "lung_cancer": (
        r"\blung cancer\b",
        r"\blung neoplasm\b",
        r"\bbronchogenic carcinoma\b",
        r"\bspiculated mass\b",
        r"\bspiculated nodule\b",
        r"\bpulmonary mass\b",
        r"\bhilar mass\b",
        r"\bsuspicious for malignancy\b",
        r"\benlarging nodule\b",
    ),
    "pneumonia": (
        r"\bpneumonia\b",
        r"\blobar consolidation\b",
        r"\bfocal consolidation\b",
        r"\bpatchy infiltrate\b",
        r"\bairspace consolidation\b",
        r"\bairspace opacity\b",
        r"\bmultifocal pneumonia\b",
        r"\bbronchopneumonia\b",
    ),
    "pleural_effusion": (
        r"\bpleural effusion\b",
        r"\bcostophrenic blunting\b",
        r"\bblunting of the costophrenic\b",
    ),
    "cardiomegaly": (
        r"\bcardiomegaly\b",
        r"\benlarged cardiac silhouette\b",
        r"\bheart is enlarged\b",
        r"\bcardiac silhouette is enlarged\b",
    ),
    "normal": (
        r"\bnormal chest\b",
        r"\bno acute cardiopulmonary abnormality\b",
        r"\bno acute cardiopulmonary process\b",
        r"\bno acute disease\b",
    ),
}


def display_label(label: str) -> str:
    return LABEL_DISPLAY_NAMES.get(normalize_label_name(label), label.replace("_", " ").title())


def normalize_label_name(label: str | None) -> str:
    if not label:
        return "other_lung_abnormality"

    cleaned = label.strip().lower().replace("-", " ").replace("/", " ")
    compact = re.sub(r"\s+", " ", cleaned)

    if compact in {"normal", "no acute cardiopulmonary abnormality"}:
        return "normal"
    if "cardiomegaly" in compact:
        return "cardiomegaly"
    if "pleural effusion" in compact:
        return "pleural_effusion"
    if "pneumonia" in compact:
        return "pneumonia"
    if "tuberculosis" in compact or compact == "tb":
        return "tuberculosis"
    if any(term in compact for term in ("lung neoplasm", "lung cancer", "carcinoma", "malignancy")):
        return "lung_cancer"
    if "other lung abnormality" in compact:
        return "other_lung_abnormality"
    return compact.replace(" ", "_")


def normalize_report_text(text: str) -> str:
    cleaned = text.lower()
    cleaned = cleaned.replace("xxxx", " ")
    cleaned = re.sub(r"[^a-z0-9\s]", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def simple_lemmatize(token: str) -> str:
    if len(token) <= 3:
        return token
    if token.endswith("ies") and len(token) > 4:
        return token[:-3] + "y"
    if token.endswith("sses"):
        return token[:-2]
    if token.endswith("ing") and len(token) > 5:
        return token[:-3]
    if token.endswith("ed") and len(token) > 4:
        return token[:-2]
    if token.endswith("s") and len(token) > 4 and not token.endswith("ss"):
        return token[:-1]
    return token


def tokenize_report(text: str, *, remove_stopwords: bool = True) -> list[str]:
    tokens = re.findall(r"[a-z0-9]+", normalize_report_text(text))
    normalized_tokens: list[str] = []
    for token in tokens:
        if token == "tb":
            normalized_tokens.append(token)
            continue

        lemma = simple_lemmatize(token)
        if remove_stopwords and lemma in MODEL_STOPWORDS:
            continue
        if len(lemma) <= 1:
            continue
        normalized_tokens.append(lemma)
    return normalized_tokens


def preprocess_report_text(text: str) -> str:
    return " ".join(tokenize_report(text, remove_stopwords=True))


def _unique_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def extract_candidate_keywords(text: str, top_k: int = 5) -> list[str]:
    tokens = tokenize_report(text, remove_stopwords=True)
    candidates: list[str] = []
    for ngram_size in (3, 2, 1):
        if len(tokens) < ngram_size:
            continue
        for index in range(len(tokens) - ngram_size + 1):
            phrase = " ".join(tokens[index : index + ngram_size])
            if len(phrase) < 4:
                continue
            candidates.append(phrase)
            if len(candidates) >= top_k * 4:
                break
        if len(candidates) >= top_k * 4:
            break

    if not candidates:
        return []
    return _unique_preserve_order(candidates)[:top_k]


def _softmax(values: np.ndarray) -> np.ndarray:
    shifted = values - np.max(values)
    exp_values = np.exp(shifted)
    total = np.sum(exp_values)
    if total <= 0:
        return np.full_like(exp_values, 1 / len(exp_values), dtype=float)
    return exp_values / total


def _find_rule_matches(text: str, label: str) -> list[str]:
    matches: list[str] = []
    for pattern in RUNTIME_RULES.get(label, ()):
        for match in re.finditer(pattern, text, re.IGNORECASE):
            start = max(0, match.start() - 60)
            context = text[start : match.end()]
            if NEGATION_PATTERN.search(context):
                continue
            matches.append(match.group(0).strip())
    return _unique_preserve_order(matches)


def _build_rule_prediction(text: str) -> tuple[str, float, list[str]] | None:
    normalized = normalize_report_text(text)
    best_label: str | None = None
    best_confidence = 0.0
    best_matches: list[str] = []

    for label in LABEL_ORDER:
        matches = _find_rule_matches(normalized, label)
        if not matches:
            continue

        confidence_floor = 0.9 if label in {"tuberculosis", "lung_cancer"} else 0.82
        confidence = min(0.99, confidence_floor + 0.03 * (len(matches) - 1))
        if confidence > best_confidence:
            best_label = label
            best_confidence = confidence
            best_matches = matches

    if best_label is not None:
        return best_label, best_confidence, best_matches[:5]

    normal_matches = _find_rule_matches(normalized, "normal")
    if normal_matches:
        return "normal", 0.78, normal_matches[:5]

    return None


class SentenceEmbeddingVectorizer:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", batch_size: int = 32) -> None:
        self.model_name = model_name
        self.batch_size = batch_size
        self._model = None

    def fit(self, texts: list[str], y: list[str] | None = None) -> "SentenceEmbeddingVectorizer":
        return self

    def transform(self, texts: list[str]) -> np.ndarray:
        model = self._get_model()
        return np.asarray(
            model.encode(
                list(texts),
                batch_size=self.batch_size,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
        )

    def fit_transform(self, texts: list[str], y: list[str] | None = None) -> np.ndarray:
        self.fit(texts, y)
        return self.transform(texts)

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer  # type: ignore

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def __getstate__(self) -> dict[str, Any]:
        state = self.__dict__.copy()
        state["_model"] = None
        return state


@dataclass(frozen=True)
class RadiologyPrediction:
    disease: str
    confidence: float
    probabilities: dict[str, float]
    top_keywords: list[str]
    model_source: str
    normalized_label: str


class RadiologyClassifierService:
    def __init__(self, model_path: Path | None = None) -> None:
        self.model_path = model_path or MODEL_PATH
        self._bundle: dict[str, Any] | None = None
        self._bundle_load_attempted = False

    def predict(self, text: str) -> RadiologyPrediction:
        normalized_text = normalize_report_text(text)
        preprocessed_text = preprocess_report_text(text)
        bundle = self._load_bundle()
        rule_prediction = _build_rule_prediction(normalized_text)

        if bundle:
            if bundle.get("vectorizer") is not None and bundle.get("classifier") is not None:
                artifact_prediction = self._predict_with_bundle(bundle, preprocessed_text, normalized_text)
                return self._merge_with_runtime_rules(artifact_prediction, rule_prediction)
            if bundle.get("pipeline") is not None:
                artifact_prediction = self._predict_with_legacy_pipeline(bundle["pipeline"], preprocessed_text, normalized_text)
                return self._merge_with_runtime_rules(artifact_prediction, rule_prediction)

        if rule_prediction is not None:
            label, confidence, matches = rule_prediction
            return RadiologyPrediction(
                disease=display_label(label),
                confidence=confidence,
                probabilities={display_label(label): confidence},
                top_keywords=matches or extract_candidate_keywords(normalized_text, top_k=5),
                model_source="runtime-rules",
                normalized_label=label,
            )

        fallback_keywords = extract_candidate_keywords(normalized_text, top_k=5)
        return RadiologyPrediction(
            disease=display_label("other_lung_abnormality"),
            confidence=0.45,
            probabilities={display_label("other_lung_abnormality"): 0.45},
            top_keywords=fallback_keywords,
            model_source="fallback",
            normalized_label="other_lung_abnormality",
        )

    def top_keywords(self, text: str, disease: str | None = None, top_k: int = 5) -> list[str]:
        normalized_text = normalize_report_text(text)
        normalized_label = normalize_label_name(disease)
        if disease:
            rule_matches = _find_rule_matches(normalized_text, normalized_label)
            if rule_matches:
                return rule_matches[:top_k]

        bundle = self._load_bundle()
        if bundle:
            if bundle.get("vectorizer") is not None and bundle.get("classifier") is not None:
                try:
                    return self._keywords_from_bundle(
                        bundle,
                        preprocess_report_text(text),
                        normalized_text,
                        normalized_label=normalized_label,
                        top_k=top_k,
                    )
                except Exception as exc:
                    logger.warning("Failed to derive classifier keywords from model bundle.", exc_info=exc)
            if bundle.get("pipeline") is not None:
                try:
                    return self._keywords_from_legacy_pipeline(bundle["pipeline"], preprocess_report_text(text), normalized_text, normalized_label, top_k)
                except Exception as exc:
                    logger.warning("Failed to derive classifier keywords from legacy pipeline.", exc_info=exc)

        return extract_candidate_keywords(normalized_text, top_k=top_k)

    def metadata(self) -> dict[str, Any]:
        bundle = self._load_bundle()
        if bundle is None:
            return {
                "available": False,
                "model_path": str(self._resolve_model_path()),
            }

        return {
            "available": True,
            "model_path": str(self._resolve_model_path()),
            "model_name": bundle.get("model_name"),
            "metrics": bundle.get("metrics", {}),
            "trained_at": bundle.get("trained_at"),
        }

    def _resolve_model_path(self) -> Path:
        if self.model_path.exists():
            return self.model_path
        if LEGACY_MODEL_PATH.exists():
            return LEGACY_MODEL_PATH
        return self.model_path

    def _load_bundle(self) -> dict[str, Any] | None:
        if self._bundle_load_attempted:
            return self._bundle

        self._bundle_load_attempted = True
        path = self._resolve_model_path()
        if not path.exists():
            logger.warning("Radiology classifier artifact not found; runtime rules will be used.", extra={"model_path": str(path)})
            self._bundle = None
            return None

        try:
            import joblib  # type: ignore

            self._bundle = joblib.load(path)
        except Exception as exc:
            logger.warning("Failed to load radiology classifier artifact; runtime rules will be used.", exc_info=exc)
            self._bundle = None
        return self._bundle

    def _merge_with_runtime_rules(
        self,
        artifact_prediction: RadiologyPrediction,
        rule_prediction: tuple[str, float, list[str]] | None,
    ) -> RadiologyPrediction:
        if rule_prediction is None:
            return artifact_prediction

        rule_label, rule_confidence, rule_matches = rule_prediction
        artifact_label = normalize_label_name(artifact_prediction.normalized_label)
        safety_labels = {"tuberculosis", "lung_cancer"}

        if rule_label == artifact_label:
            merged_keywords = _unique_preserve_order(rule_matches + artifact_prediction.top_keywords)
            probabilities = dict(artifact_prediction.probabilities)
            probabilities[display_label(rule_label)] = max(
                probabilities.get(display_label(rule_label), 0.0),
                round(max(artifact_prediction.confidence, rule_confidence), 4),
            )
            return RadiologyPrediction(
                disease=artifact_prediction.disease,
                confidence=max(artifact_prediction.confidence, rule_confidence),
                probabilities=probabilities,
                top_keywords=merged_keywords[:5],
                model_source=artifact_prediction.model_source,
                normalized_label=artifact_prediction.normalized_label,
            )

        if rule_label in safety_labels and rule_confidence >= max(artifact_prediction.confidence + 0.05, 0.9):
            probabilities = dict(artifact_prediction.probabilities)
            probabilities[display_label(rule_label)] = round(rule_confidence, 4)
            return RadiologyPrediction(
                disease=display_label(rule_label),
                confidence=rule_confidence,
                probabilities=probabilities,
                top_keywords=rule_matches[:5] or artifact_prediction.top_keywords,
                model_source=f"{artifact_prediction.model_source}+safety-rule",
                normalized_label=rule_label,
            )

        if artifact_prediction.confidence < 0.45 and rule_confidence > artifact_prediction.confidence:
            return RadiologyPrediction(
                disease=display_label(rule_label),
                confidence=rule_confidence,
                probabilities={display_label(rule_label): rule_confidence},
                top_keywords=rule_matches[:5] or artifact_prediction.top_keywords,
                model_source="runtime-rules",
                normalized_label=rule_label,
            )

        return artifact_prediction

    def _predict_with_bundle(self, bundle: dict[str, Any], preprocessed_text: str, normalized_text: str) -> RadiologyPrediction:
        vectorizer = bundle["vectorizer"]
        classifier = bundle["classifier"]
        label_encoder = bundle.get("label_encoder")

        features = vectorizer.transform([preprocessed_text])
        probabilities, class_names = self._predict_probabilities(classifier, features, label_encoder=label_encoder)
        predicted_index = int(np.argmax(probabilities))
        predicted_label = normalize_label_name(class_names[predicted_index])

        probability_map = {
            display_label(label): float(round(score, 4))
            for label, score in zip(class_names, probabilities, strict=False)
        }
        keywords = self._keywords_from_bundle(
            bundle,
            preprocessed_text,
            normalized_text,
            normalized_label=predicted_label,
            top_k=5,
        )

        return RadiologyPrediction(
            disease=display_label(predicted_label),
            confidence=float(probabilities[predicted_index]),
            probabilities=probability_map,
            top_keywords=keywords,
            model_source=str(bundle.get("model_name", "artifact")),
            normalized_label=predicted_label,
        )

    def _predict_with_legacy_pipeline(self, pipeline: Any, preprocessed_text: str, normalized_text: str) -> RadiologyPrediction:
        probabilities = pipeline.predict_proba([preprocessed_text])[0]
        class_names = [normalize_label_name(label) for label in pipeline.classes_]
        predicted_index = int(np.argmax(probabilities))
        predicted_label = class_names[predicted_index]
        keywords = self._keywords_from_legacy_pipeline(pipeline, preprocessed_text, normalized_text, predicted_label, top_k=5)
        return RadiologyPrediction(
            disease=display_label(predicted_label),
            confidence=float(probabilities[predicted_index]),
            probabilities={
                display_label(label): float(round(score, 4))
                for label, score in zip(class_names, probabilities, strict=False)
            },
            top_keywords=keywords,
            model_source="legacy-pipeline",
            normalized_label=predicted_label,
        )

    def _predict_probabilities(
        self,
        classifier: Any,
        features: Any,
        *,
        label_encoder: Any | None = None,
    ) -> tuple[np.ndarray, list[str]]:
        if label_encoder is not None:
            class_names = [normalize_label_name(label) for label in label_encoder.classes_]
        elif hasattr(classifier, "classes_"):
            class_names = [normalize_label_name(label) for label in classifier.classes_]
        else:
            class_names = []

        if hasattr(classifier, "predict_proba"):
            probabilities = np.asarray(classifier.predict_proba(features)[0], dtype=float)
            if not class_names:
                class_names = [normalize_label_name(label) for label in classifier.classes_]
            return probabilities, class_names

        if hasattr(classifier, "decision_function"):
            decision = classifier.decision_function(features)
            decision = np.asarray(decision, dtype=float)
            if decision.ndim == 1:
                probabilities = _softmax(np.array([-decision[0], decision[0]], dtype=float))
                if not class_names and hasattr(classifier, "classes_"):
                    class_names = [normalize_label_name(label) for label in classifier.classes_]
            else:
                probabilities = _softmax(decision[0])
                if not class_names and hasattr(classifier, "classes_"):
                    class_names = [normalize_label_name(label) for label in classifier.classes_]
            return probabilities, class_names

        predicted = classifier.predict(features)
        predicted_label = normalize_label_name(
            label_encoder.inverse_transform(predicted)[0] if label_encoder is not None else predicted[0]
        )
        return np.asarray([1.0], dtype=float), [predicted_label]

    def _keywords_from_bundle(
        self,
        bundle: dict[str, Any],
        preprocessed_text: str,
        normalized_text: str,
        *,
        normalized_label: str,
        top_k: int,
    ) -> list[str]:
        vectorizer = bundle.get("explain_vectorizer") or bundle.get("vectorizer")
        classifier = bundle.get("explain_classifier") or bundle.get("classifier")
        if vectorizer is None or classifier is None:
            return extract_candidate_keywords(normalized_text, top_k=top_k)

        if not hasattr(vectorizer, "get_feature_names_out"):
            return extract_candidate_keywords(normalized_text, top_k=top_k)

        features = vectorizer.transform([preprocessed_text])
        return self._keywords_from_features(
            vectorizer=vectorizer,
            classifier=classifier,
            features=features,
            normalized_text=normalized_text,
            normalized_label=normalized_label,
            top_k=top_k,
        )

    def _keywords_from_legacy_pipeline(
        self,
        pipeline: Any,
        preprocessed_text: str,
        normalized_text: str,
        normalized_label: str,
        top_k: int,
    ) -> list[str]:
        try:
            vectorizer = pipeline.named_steps["tfidf"]
            classifier = pipeline.named_steps["clf"]
        except Exception:
            return extract_candidate_keywords(normalized_text, top_k=top_k)

        features = vectorizer.transform([preprocessed_text])
        return self._keywords_from_features(
            vectorizer=vectorizer,
            classifier=classifier,
            features=features,
            normalized_text=normalized_text,
            normalized_label=normalized_label,
            top_k=top_k,
        )

    def _keywords_from_features(
        self,
        *,
        vectorizer: Any,
        classifier: Any,
        features: Any,
        normalized_text: str,
        normalized_label: str,
        top_k: int,
    ) -> list[str]:
        try:
            feature_names = vectorizer.get_feature_names_out()
            if hasattr(classifier, "coef_"):
                class_names = [normalize_label_name(label) for label in getattr(classifier, "classes_", [])]
                class_index = class_names.index(normalized_label) if normalized_label in class_names else 0
                if getattr(classifier.coef_, "shape", (0, 0))[0] == 1 and len(class_names) == 2:
                    coefficient_vector = classifier.coef_[0] if class_index == 1 else -classifier.coef_[0]
                else:
                    coefficient_vector = classifier.coef_[class_index]
                contributions = [
                    (float(value) * float(coefficient_vector[index]), str(feature_names[index]))
                    for index, value in zip(features.indices, features.data, strict=False)
                    if float(value) * float(coefficient_vector[index]) > 0
                ]
            elif hasattr(classifier, "feature_importances_"):
                contributions = [
                    (float(value) * float(classifier.feature_importances_[index]), str(feature_names[index]))
                    for index, value in zip(features.indices, features.data, strict=False)
                    if float(value) * float(classifier.feature_importances_[index]) > 0
                ]
            else:
                contributions = []

            contributions.sort(key=lambda item: item[0], reverse=True)
            keywords = _unique_preserve_order([feature for _, feature in contributions])
            if keywords:
                return keywords[:top_k]
        except Exception as exc:
            logger.warning("Unable to derive feature contributions from trained model.", exc_info=exc)

        return extract_candidate_keywords(normalized_text, top_k=top_k)


@lru_cache(maxsize=1)
def get_radiology_classifier() -> RadiologyClassifierService:
    return RadiologyClassifierService()

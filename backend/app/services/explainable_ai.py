from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from functools import lru_cache

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_MEDICAL_TERMS = [
    "cardiomegaly",
    "pleural effusion",
    "pneumothorax",
    "consolidation",
    "atelectasis",
    "pulmonary edema",
    "lung opacity",
    "ground glass",
    "fracture",
    "nodule",
    "mass",
]

_STOPWORDS = {
    "the",
    "and",
    "with",
    "from",
    "this",
    "that",
    "there",
    "were",
    "which",
    "will",
    "your",
    "have",
    "been",
    "into",
    "findings",
}

_DISEASE_EXPLANATIONS = {
    "cardiomegaly": "cardiomegaly strongly indicates heart enlargement",
    "pleural effusion": "pleural effusion suggests fluid around the lungs",
    "pneumothorax": "pneumothorax indicates air in the pleural space",
    "pneumonia": "pneumonia is supported by consolidation-related findings",
    "pulmonary edema": "pulmonary edema is associated with fluid overload in the lungs",
}


@dataclass(frozen=True)
class ExplanationResult:
    highlighted_terms: list[str]
    explanation: str
    token_importance: list[tuple[str, float]] | None = None

    def to_dict(self) -> dict:
        return {
            "highlighted_terms": self.highlighted_terms,
            "explanation": self.explanation,
        }


@lru_cache(maxsize=2)
def _get_transformer_objects(model_name: str):
    try:
        import torch  # type: ignore
        from transformers import AutoModel, AutoTokenizer  # type: ignore

        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModel.from_pretrained(model_name, output_attentions=True)
        model.eval()
        return tokenizer, model, torch
    except Exception as exc:
        logger.warning("Transformer model load failed; using rule-based explanations.", exc_info=exc)
        return None, None, None


class ExplainableAIService:
    """Reusable explainability service for radiology NLP predictions."""

    def __init__(self, model_name: str | None = None) -> None:
        settings = get_settings()
        self.model_name = model_name or settings.hf_model_name

    def explain(
        self,
        text: str,
        prediction_label: str,
        top_k: int = 6,
    ) -> ExplanationResult:
        try:
            highlighted = self._extract_evidence_terms(text, prediction_label, top_k)
            explanation = self._build_explanation(prediction_label, highlighted)
            token_scores = self._token_importance_scores(text)
        except Exception as exc:
            logger.warning("Explainability failed; returning minimal response.", exc_info=exc)
            highlighted = ["no acute findings"]
            explanation = f"findings support prediction of {prediction_label}"
            token_scores = None
        return ExplanationResult(
            highlighted_terms=highlighted,
            explanation=explanation,
            token_importance=token_scores,
        )

    def _extract_evidence_terms(self, text: str, prediction_label: str, top_k: int) -> list[str]:
        text_lower = text.lower()
        evidence = []

        for term in _MEDICAL_TERMS:
            if term in text_lower:
                evidence.append(term)

        pred_lower = prediction_label.lower()
        if pred_lower in text_lower and pred_lower not in evidence:
            evidence.insert(0, pred_lower)

        if not evidence:
            evidence = self._fallback_terms(text)

        # Deduplicate while preserving order
        deduped: list[str] = []
        for term in evidence:
            if term and term not in deduped:
                deduped.append(term)
            if len(deduped) >= top_k:
                break

        return deduped[:top_k] if deduped else ["no acute findings"]

    def _build_explanation(self, prediction_label: str, highlights: list[str]) -> str:
        pred_lower = prediction_label.lower()
        if pred_lower in _DISEASE_EXPLANATIONS:
            return _DISEASE_EXPLANATIONS[pred_lower]
        if highlights:
            return f"{highlights[0]} supports prediction of {prediction_label}"
        return f"findings support prediction of {prediction_label}"

    def _fallback_terms(self, text: str) -> list[str]:
        tokens = re.findall(r"[a-zA-Z]{4,}", text.lower())
        filtered = [t for t in tokens if t not in _STOPWORDS]
        return list(dict.fromkeys(filtered))[:5]

    def _token_importance_scores(self, text: str) -> list[tuple[str, float]] | None:
        try:
            tokenizer, model, torch = _get_transformer_objects(self.model_name)
            if tokenizer is None or model is None or torch is None:
                return None

            inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=256)
            with torch.no_grad():
                outputs = model(**inputs)

            attentions = outputs.attentions
            if not attentions:
                return None

            attn = torch.stack(attentions).mean(dim=0).mean(dim=1)  # B x S x S
            cls_attn = attn[0, 0]
            scores = cls_attn / (cls_attn.sum() + 1e-12)
            tokens = tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])

            token_scores = list(zip(tokens, scores.tolist(), strict=False))
            token_scores.sort(key=lambda x: x[1], reverse=True)
            return token_scores[:20]
        except Exception as exc:
            logger.warning("Token scoring failed; using rule-based highlights.", exc_info=exc)
            return None


def explain_to_json(text: str, prediction_label: str) -> dict:
    service = ExplainableAIService()
    return service.explain(text=text, prediction_label=prediction_label).to_dict()

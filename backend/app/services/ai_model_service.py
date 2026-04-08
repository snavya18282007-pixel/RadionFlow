from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class Finding:
    label: str
    confidence: float
    evidence: str | None = None


class AIModelService:
    def __init__(self) -> None:
        settings = get_settings()
        self._torch_available = False
        try:
            import torch  # type: ignore

            self._torch_available = True
            self._device = 0 if settings.hf_device == "cuda" and torch.cuda.is_available() else -1
        except Exception:  # pragma: no cover - platform-specific
            logger.info("Torch not available; using CPU-safe fallbacks.")
            self._device = -1
        self._zero_shot = None
        self._classifier = None
        self._model_name = settings.hf_model_name
        self._zero_shot_model = settings.hf_zero_shot_model

    def _load_zero_shot(self):
        if self._zero_shot is None:
            logger.info("Loading zero-shot model")
            try:
                from transformers import pipeline  # type: ignore

                self._zero_shot = pipeline(
                    "zero-shot-classification",
                    model=self._zero_shot_model,
                    device=self._device,
                )
            except Exception as exc:
                logger.warning("Failed to load zero-shot pipeline.", exc_info=exc)
                raise
        return self._zero_shot

    def _load_classifier(self):
        if self._classifier is None:
            logger.info("Loading text-classification model")
            try:
                from transformers import pipeline  # type: ignore

                self._classifier = pipeline("text-classification", model=self._model_name, device=self._device)
            except Exception as exc:
                logger.warning("Failed to load text-classification pipeline.", exc_info=exc)
                raise
        return self._classifier

    def extract_findings(self, text: str) -> list[Finding]:
        patterns = {
            "pulmonary nodule": r"nodule",
            "pneumonia": r"pneumonia|consolidation",
            "pleural effusion": r"effusion",
            "fracture": r"fracture",
            "atelectasis": r"atelectasis",
        }
        findings: list[Finding] = []
        for label, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                findings.append(Finding(label=label, confidence=0.85, evidence=match.group(0)))
        if not findings:
            findings.append(Finding(label="no acute findings", confidence=0.6))
        return findings

    def classify_disease(self, text: str, labels: list[str]) -> dict[str, float]:
        try:
            zero_shot = self._load_zero_shot()
            result = zero_shot(text, labels)
            return {label: float(score) for label, score in zip(result["labels"], result["scores"], strict=False)}
        except Exception as exc:
            logger.warning("Zero-shot classification failed; falling back to rules", exc_info=exc)
            scores = {label: 0.0 for label in labels}
            for label in labels:
                if label.lower() in text.lower():
                    scores[label] = 0.7
            if not any(scores.values()):
                scores[labels[0]] = 0.5
            return scores

    def explain(self, text: str, top_k: int = 5) -> dict[str, Any]:
        tokens = re.findall(r"[A-Za-z]{4,}", text)
        tokens = list(dict.fromkeys(tokens))
        return {"top_tokens": tokens[:top_k]}


@lru_cache(maxsize=1)
def get_model_service() -> AIModelService:
    return AIModelService()

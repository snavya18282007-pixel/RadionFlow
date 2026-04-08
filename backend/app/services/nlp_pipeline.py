from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable

logger = logging.getLogger(__name__)


DEFAULT_FINDINGS = [
    "cardiomegaly",
    "pleural effusion",
    "pneumothorax",
    "consolidation",
    "atelectasis",
    "pulmonary edema",
    "pulmonary nodule",
    "fracture",
    "opacity",
]

DEFAULT_DISEASE_LABELS = [
    "Pleural Effusion",
    "Pneumonia",
    "Pulmonary Edema",
    "Pneumothorax",
    "Cardiomegaly",
    "Normal",
]


@dataclass(frozen=True)
class ClassificationResult:
    disease: str
    confidence: float
    probabilities: dict[str, float]


@dataclass(frozen=True)
class PipelineOutput:
    findings: list[str]
    disease: str
    confidence: float
    triage_level: str
    explanation: list[str]


class ModelLoader:
    """Lazy-loading wrapper for NLP models used in the pipeline."""

    def __init__(
        self,
        *,
        spacy_model: str = "en_core_web_sm",
        clinical_bert_model: str = "emilyalsentzer/Bio_ClinicalBERT",
    ) -> None:
        self.spacy_model = spacy_model
        self.clinical_bert_model = clinical_bert_model
        self._nlp = None
        self._hf_tokenizer = None
        self._hf_model = None
        self._torch = None

    def _load_torch(self):
        if self._torch is not None:
            return self._torch
        try:
            import torch  # type: ignore

            self._torch = torch
            return torch
        except Exception as exc:  # pragma: no cover - platform specific
            logger.warning("Torch not available; falling back to rules.", exc_info=exc)
            self._torch = None
            return None

    def load_spacy(self):
        if self._nlp is not None:
            return self._nlp
        try:
            # Requires: python -m spacy download en_core_web_sm
            import spacy  # type: ignore

            self._nlp = spacy.load(self.spacy_model)
        except Exception as exc:
            logger.warning("spaCy model load failed; using blank English pipeline.", exc_info=exc)
            import spacy  # type: ignore

            self._nlp = spacy.blank("en")
        return self._nlp

    def load_clinical_bert(self):
        if self._hf_model is not None and self._hf_tokenizer is not None:
            return self._hf_tokenizer, self._hf_model

        torch = self._load_torch()
        if torch is None:
            return None, None
        try:
            from transformers import AutoModel, AutoTokenizer  # type: ignore

            self._hf_tokenizer = AutoTokenizer.from_pretrained(self.clinical_bert_model)
            self._hf_model = AutoModel.from_pretrained(self.clinical_bert_model)
            self._hf_model.eval()
            return self._hf_tokenizer, self._hf_model
        except Exception as exc:
            logger.warning("ClinicalBERT load failed; falling back to rules.", exc_info=exc)
            return None, None


class RadiologyNLPPipeline:
    """Modular NLP pipeline for radiology report analysis."""

    def __init__(
        self,
        model_loader: ModelLoader | None = None,
        findings_vocab: Iterable[str] | None = None,
        disease_labels: Iterable[str] | None = None,
    ) -> None:
        self.model_loader = model_loader or ModelLoader()
        self.findings_vocab = [f.lower() for f in (findings_vocab or DEFAULT_FINDINGS)]
        self.disease_labels = list(disease_labels or DEFAULT_DISEASE_LABELS)

    def extract_findings(self, text: str) -> list[str]:
        """Extract medical findings using spaCy NER + phrase matching."""
        nlp = self.model_loader.load_spacy()
        doc = nlp(text)

        # NER-derived candidates
        candidates = {ent.text.lower() for ent in doc.ents}

        # Phrase matching by vocab
        text_lower = text.lower()
        for term in self.findings_vocab:
            if term in text_lower:
                candidates.add(term)

        findings = sorted({c for c in candidates if any(t in c for t in self.findings_vocab)})
        if not findings:
            findings = ["no acute findings"]
        return findings

    def classify_disease(self, text: str) -> ClassificationResult:
        """Classify disease categories using ClinicalBERT embeddings."""
        tokenizer, model = self.model_loader.load_clinical_bert()
        torch = self.model_loader._load_torch()

        if tokenizer is None or model is None or torch is None:
            # Rule-based fallback
            probs = {label: 0.0 for label in self.disease_labels}
            text_lower = text.lower()
            for label in self.disease_labels:
                if label.lower() in text_lower:
                    probs[label] = 0.7
            if not any(probs.values()):
                probs[self.disease_labels[-1]] = 0.5  # "Normal"
            disease = max(probs, key=probs.get)
            return ClassificationResult(disease=disease, confidence=float(probs[disease]), probabilities=probs)

        def _embed(sentence: str) -> "torch.Tensor":
            tokens = tokenizer(sentence, return_tensors="pt", truncation=True, max_length=256)
            with torch.no_grad():
                output = model(**tokens)
            cls = output.last_hidden_state[:, 0, :]
            return cls / (cls.norm(dim=-1, keepdim=True) + 1e-12)

        text_vec = _embed(text)
        label_vecs = []
        for label in self.disease_labels:
            label_vecs.append(_embed(f"Radiology finding: {label}"))
        label_mat = torch.cat(label_vecs, dim=0)
        sims = (label_mat @ text_vec.T).squeeze(dim=1)
        probs_t = torch.softmax(sims, dim=0)
        probs = {label: float(prob) for label, prob in zip(self.disease_labels, probs_t.tolist(), strict=False)}
        disease = max(probs, key=probs.get)
        return ClassificationResult(disease=disease, confidence=float(probs[disease]), probabilities=probs)

    def compute_triage_score(self, disease: str, findings: list[str]) -> tuple[str, float]:
        """Assign urgency level based on disease and findings."""
        disease_lower = disease.lower()
        score = 0.2
        if "pneumothorax" in disease_lower:
            score = 0.9
        elif "pulmonary edema" in disease_lower:
            score = 0.8
        elif "pneumonia" in disease_lower:
            score = 0.7
        elif "pleural effusion" in disease_lower:
            score = 0.6
        elif "cardiomegaly" in disease_lower:
            score = 0.5

        if any("fracture" in f for f in findings):
            score = max(score, 0.75)

        if score >= 0.8:
            level = "HIGH"
        elif score >= 0.5:
            level = "MEDIUM"
        else:
            level = "LOW"
        return level, score

    def generate_explanation(self, findings: list[str], disease: str) -> list[str]:
        """Generate explainable evidence based on extracted findings."""
        evidence = []
        for finding in findings:
            if finding == "no acute findings":
                continue
            evidence.append(f"{finding} detected in report")
        if not evidence:
            evidence.append(f"no acute findings; classified as {disease}")
        return evidence

    def run(self, text: str) -> PipelineOutput:
        findings = self.extract_findings(text)
        classification = self.classify_disease(text)
        triage_level, _ = self.compute_triage_score(classification.disease, findings)
        explanation = self.generate_explanation(findings, classification.disease)
        return PipelineOutput(
            findings=findings,
            disease=classification.disease,
            confidence=classification.confidence,
            triage_level=triage_level,
            explanation=explanation,
        )


@lru_cache
def get_pipeline() -> RadiologyNLPPipeline:
    return RadiologyNLPPipeline()


if __name__ == "__main__":
    sample_text = "Moderate cardiomegaly and small pleural effusion. No pneumothorax."
    pipeline = get_pipeline()
    output = pipeline.run(sample_text)
    print(output)

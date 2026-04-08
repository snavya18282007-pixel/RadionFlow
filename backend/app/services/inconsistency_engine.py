from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Iterable

logger = logging.getLogger(__name__)


NEGATION_PHRASES = [
    "no abnormality",
    "no abnormalities",
    "no acute",
    "no acute findings",
    "within normal limits",
    "unremarkable",
    "normal study",
    "no evidence of",
]

POSITIVE_FINDINGS = [
    "pleural effusion",
    "pneumothorax",
    "consolidation",
    "fracture",
    "mass",
    "nodule",
    "cardiomegaly",
    "pulmonary edema",
    "edema",
    "opacity",
    "atelectasis",
    "hemorrhage",
]


@dataclass(frozen=True)
class InconsistencyResult:
    inconsistency_detected: bool
    reason: str | None
    evidence: list[str]

    def to_dict(self) -> dict:
        return {
            "inconsistency_detected": self.inconsistency_detected,
            "reason": self.reason,
            "evidence": self.evidence,
        }


class InconsistencyDetector:
    """Rule-based + NLP-assisted detection of logical contradictions."""

    def __init__(
        self,
        *,
        negation_phrases: Iterable[str] | None = None,
        positive_findings: Iterable[str] | None = None,
        spacy_model: str = "en_core_sci_sm",
    ) -> None:
        self.negation_phrases = [p.lower() for p in (negation_phrases or NEGATION_PHRASES)]
        self.positive_findings = [p.lower() for p in (positive_findings or POSITIVE_FINDINGS)]
        self.spacy_model = spacy_model
        self._nlp = None

    def _load_spacy(self):
        if self._nlp is not None:
            return self._nlp
        try:
            import spacy  # type: ignore

            model_candidates = [self.spacy_model, "en_core_web_sm"]
            for model_name in model_candidates:
                try:
                    self._nlp = spacy.load(model_name)
                    self.spacy_model = model_name
                    break
                except Exception:
                    continue
        except Exception:
            self._nlp = None

        if self._nlp is None:
            logger.info("spaCy model load failed; using keyword-only inconsistency checks.")
            self._nlp = None
        return self._nlp

    def detect(self, text: str) -> InconsistencyResult:
        text_lower = text.lower()
        neg_hits = [p for p in self.negation_phrases if p in text_lower]

        findings_found = self._extract_findings(text)
        positive_hits = [p for p in findings_found if p in self.positive_findings]

        reasons = []
        evidence = []

        if neg_hits and positive_hits:
            reasons.append(
                f"Report mentions {', '.join(positive_hits)} but also states {', '.join(neg_hits)}."
            )
            evidence.extend(positive_hits)
            evidence.extend(neg_hits)

        # Detect contradictions like "no evidence of X" but X appears elsewhere.
        for finding in self.positive_findings:
            pattern = rf"no evidence of {re.escape(finding)}"
            if re.search(pattern, text_lower) and finding in text_lower.replace(
                f"no evidence of {finding}", ""
            ):
                reasons.append(f"Negated '{finding}' but later mentioned elsewhere.")
                evidence.append(finding)

        if reasons:
            return InconsistencyResult(
                inconsistency_detected=True,
                reason=" ".join(reasons),
                evidence=sorted(set(evidence)),
            )

        return InconsistencyResult(
            inconsistency_detected=False,
            reason=None,
            evidence=[],
        )

    def _extract_findings(self, text: str) -> list[str]:
        nlp = self._load_spacy()
        text_lower = text.lower()
        candidates = set()
        if nlp is not None:
            doc = nlp(text)
            candidates.update(ent.text.lower() for ent in doc.ents)
        for term in self.positive_findings:
            if term in text_lower:
                candidates.add(term)
        return sorted(candidates)

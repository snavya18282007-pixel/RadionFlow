from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

logger = logging.getLogger(__name__)

NEGATION_WINDOW = 64
SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+|\n+")
NEGATION_CUES = (
    "no evidence of",
    "no radiographic evidence of",
    "negative for",
    "free of",
    "without",
    "no",
)

FINDING_TERMS: dict[str, tuple[str, ...]] = {
    "pleural effusion": (
        "pleural effusion",
        "costophrenic blunting",
        "blunting of the costophrenic angle",
    ),
    "pneumothorax": ("pneumothorax",),
    "consolidation": (
        "consolidation",
        "airspace opacity",
        "airspace consolidation",
        "focal consolidation",
        "lobar consolidation",
        "patchy infiltrate",
    ),
    "pneumonia": (
        "pneumonia",
        "bronchopneumonia",
        "multifocal pneumonia",
    ),
    "cardiomegaly": (
        "cardiomegaly",
        "enlarged cardiac silhouette",
        "heart is enlarged",
        "cardiac silhouette is enlarged",
    ),
    "atelectasis": ("atelectasis",),
    "pulmonary nodule": (
        "pulmonary nodule",
        "spiculated nodule",
        "enlarging nodule",
        "solitary nodule",
        "lung nodule",
    ),
    "lung mass": (
        "pulmonary mass",
        "lung mass",
        "hilar mass",
        "spiculated mass",
    ),
    "tuberculosis": (
        "tuberculosis",
        "tb",
        "cavitary lesion",
        "cavitary opacity",
        "fibrocavitary",
        "apical pleural thickening",
        "upper lobe infiltrate",
        "granulomatous disease",
    ),
    "fracture": ("fracture",),
}


@dataclass(frozen=True)
class NegationProcessingResult:
    positive_findings: list[str]
    negated_findings: list[str]
    cleaned_text: str
    engine: str

    @property
    def all_findings_negated(self) -> bool:
        return bool(self.negated_findings) and not self.positive_findings


@dataclass(frozen=True)
class _FindingMatch:
    label: str
    matched_text: str
    start: int
    end: int
    negated: bool


def _unique_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def _split_sentences(text: str) -> list[tuple[str, int]]:
    sentences: list[tuple[str, int]] = []
    cursor = 0
    for chunk in SENTENCE_SPLIT_PATTERN.split(text):
        stripped = chunk.strip()
        if not stripped:
            cursor += len(chunk)
            continue
        start = text.find(chunk, cursor)
        cursor = start + len(chunk)
        sentences.append((chunk, start))
    if not sentences and text.strip():
        sentences.append((text, 0))
    return sentences


def _build_patterns() -> dict[str, tuple[re.Pattern[str], ...]]:
    patterns: dict[str, tuple[re.Pattern[str], ...]] = {}
    for label, aliases in FINDING_TERMS.items():
        compiled = tuple(
            re.compile(rf"\b{re.escape(alias)}\b", re.IGNORECASE)
            for alias in aliases
        )
        patterns[label] = compiled
    return patterns


COMPILED_PATTERNS = _build_patterns()


class RuleBasedNegationProcessor:
    def process(self, text: str) -> NegationProcessingResult:
        positive_findings: list[str] = []
        negated_findings: list[str] = []
        cleaned_sentences: list[str] = []

        for sentence, _ in _split_sentences(text):
            matches = self._match_sentence(sentence)
            if not matches:
                cleaned_sentences.append(sentence.strip())
                continue

            positive_findings.extend(match.label for match in matches if not match.negated)
            negated_findings.extend(match.label for match in matches if match.negated)

            positive_matches = [match for match in matches if not match.negated]
            if not positive_matches:
                continue

            cleaned_sentence = sentence
            for match in sorted((item for item in matches if item.negated), key=lambda item: item.start, reverse=True):
                start, end = self._expand_negated_span(cleaned_sentence, match.start, match.end)
                cleaned_sentence = f"{cleaned_sentence[:start]} {cleaned_sentence[end:]}"
            cleaned_sentence = re.sub(r"\s+", " ", cleaned_sentence).strip(" ,;:")
            if cleaned_sentence:
                cleaned_sentences.append(cleaned_sentence)

        cleaned_text = " ".join(part for part in cleaned_sentences if part).strip()
        return NegationProcessingResult(
            positive_findings=_unique_preserve_order(positive_findings),
            negated_findings=_unique_preserve_order(negated_findings),
            cleaned_text=cleaned_text,
            engine="rule-based",
        )

    def _match_sentence(self, sentence: str) -> list[_FindingMatch]:
        matches: list[_FindingMatch] = []
        lowered = sentence.lower()
        for label, patterns in COMPILED_PATTERNS.items():
            for pattern in patterns:
                for match in pattern.finditer(sentence):
                    context_start = max(0, match.start() - NEGATION_WINDOW)
                    context = lowered[context_start : match.start()]
                    negated = any(cue in context for cue in NEGATION_CUES)
                    matches.append(
                        _FindingMatch(
                            label=label,
                            matched_text=match.group(0),
                            start=match.start(),
                            end=match.end(),
                            negated=negated,
                        )
                    )
        matches.sort(key=lambda item: (item.start, item.end))
        deduped: list[_FindingMatch] = []
        seen: set[tuple[str, int, int, bool]] = set()
        for match in matches:
            key = (match.label, match.start, match.end, match.negated)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(match)
        return deduped

    @staticmethod
    def _expand_negated_span(sentence: str, start: int, end: int) -> tuple[int, int]:
        lowered = sentence.lower()
        expanded_start = start
        prefix = lowered[max(0, start - NEGATION_WINDOW) : start]
        for cue in NEGATION_CUES:
            cue_index = prefix.rfind(cue)
            if cue_index >= 0:
                expanded_start = max(0, start - len(prefix) + cue_index)
                break
        return expanded_start, end


class MedSpaCyNegationProcessor:
    def __init__(self) -> None:
        import medspacy  # type: ignore
        from medspacy.ner import TargetRule  # type: ignore

        self.nlp = medspacy.load()
        self.target_matcher = self.nlp.get_pipe("medspacy_target_matcher")

        rules = []
        for label, aliases in FINDING_TERMS.items():
            for alias in aliases:
                rules.append(TargetRule(alias, label))
        self.target_matcher.add(rules)

    def process(self, text: str) -> NegationProcessingResult:
        doc = self.nlp(text)
        positive_findings: list[str] = []
        negated_findings: list[str] = []
        negated_spans: list[tuple[int, int]] = []

        for ent in doc.ents:
            label = ent.label_.replace("_", " ").lower()
            if getattr(ent._, "is_negated", False):
                negated_findings.append(label)
                negated_spans.append((ent.start_char, ent.end_char))
            else:
                positive_findings.append(label)

        cleaned_text = self._remove_negated_spans(text, negated_spans)
        return NegationProcessingResult(
            positive_findings=_unique_preserve_order(positive_findings),
            negated_findings=_unique_preserve_order(negated_findings),
            cleaned_text=cleaned_text,
            engine="medspacy",
        )

    @staticmethod
    def _remove_negated_spans(text: str, spans: list[tuple[int, int]]) -> str:
        if not spans:
            return text.strip()
        cleaned = text
        for start, end in sorted(spans, reverse=True):
            cleaned = f"{cleaned[:start]} {cleaned[end:]}"
        return re.sub(r"\s+", " ", cleaned).strip()


@lru_cache(maxsize=1)
def _get_processor() -> Any:
    try:
        return MedSpaCyNegationProcessor()
    except ModuleNotFoundError:
        logger.info("medSpaCy not installed; using rule-based negation fallback.")
        return RuleBasedNegationProcessor()
    except Exception as exc:
        logger.warning("medSpaCy negation initialization failed; using rule-based fallback.", exc_info=exc)
        return RuleBasedNegationProcessor()


def process_radiology_text(text: str) -> NegationProcessingResult:
    processor = _get_processor()
    return processor.process(text)

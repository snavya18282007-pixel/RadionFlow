from __future__ import annotations

from app.schemas.report import InconsistencyResponse
from app.services.inconsistency_engine import InconsistencyDetector


class InconsistencyService:
    def __init__(self) -> None:
        self.detector = InconsistencyDetector()

    def detect(self, text: str) -> InconsistencyResponse:
        result = self.detector.detect(text)
        return InconsistencyResponse(
            detected=result.inconsistency_detected,
            reason=result.reason,
            details=result.evidence,
        )

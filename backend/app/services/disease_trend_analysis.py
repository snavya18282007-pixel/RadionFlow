from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db import TriageResult
from app.schemas.report import TrendAnalysisResponse


def build_empty_trend_analysis(disease: str) -> TrendAnalysisResponse:
    return TrendAnalysisResponse(
        disease=disease,
        recent_case_count=0,
        previous_case_count=0,
        critical_case_count=0,
        window_days=14,
        trend_direction="insufficient_data",
        summary="Trend analysis will populate as more historical radiology cases are accumulated.",
    )


class DiseaseTrendAnalysisService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def analyze(self, disease: str, *, window_days: int = 14) -> TrendAnalysisResponse:
        if not disease or disease.lower() == "normal":
            return TrendAnalysisResponse(
                disease=disease or "Normal",
                recent_case_count=0,
                previous_case_count=0,
                critical_case_count=0,
                window_days=window_days,
                trend_direction="stable",
                summary="Normal studies are not tracked as a disease trend.",
            )

        now = datetime.now(timezone.utc)
        recent_start = now - timedelta(days=window_days)
        previous_start = now - timedelta(days=window_days * 2)

        recent_case_count = await self._count_cases(disease, start=recent_start, end=now)
        previous_case_count = await self._count_cases(disease, start=previous_start, end=recent_start)
        critical_case_count = await self._count_cases(
            disease,
            start=recent_start,
            end=now,
            urgency_levels=("CRITICAL", "HIGH"),
        )

        if previous_case_count == 0 and recent_case_count == 0:
            trend_direction = "insufficient_data"
        elif recent_case_count > previous_case_count:
            trend_direction = "increasing"
        elif recent_case_count < previous_case_count:
            trend_direction = "decreasing"
        else:
            trend_direction = "stable"

        if trend_direction == "increasing":
            summary = (
                f"{disease} cases increased to {recent_case_count} in the last {window_days} days "
                f"from {previous_case_count} in the preceding window."
            )
        elif trend_direction == "decreasing":
            summary = (
                f"{disease} cases decreased to {recent_case_count} in the last {window_days} days "
                f"from {previous_case_count} in the preceding window."
            )
        elif trend_direction == "stable":
            summary = f"{disease} volume is stable with {recent_case_count} recent cases."
        else:
            summary = "There is not enough historical data yet to infer a disease trend."

        return TrendAnalysisResponse(
            disease=disease,
            recent_case_count=recent_case_count,
            previous_case_count=previous_case_count,
            critical_case_count=critical_case_count,
            window_days=window_days,
            trend_direction=trend_direction,
            summary=summary,
        )

    async def _count_cases(
        self,
        disease: str,
        *,
        start: datetime,
        end: datetime,
        urgency_levels: tuple[str, ...] | None = None,
    ) -> int:
        stmt = select(func.count(TriageResult.id)).where(
            TriageResult.disease_prediction == disease,
            TriageResult.created_at >= start,
            TriageResult.created_at < end,
        )
        if urgency_levels:
            stmt = stmt.where(TriageResult.urgency_level.in_(urgency_levels))
        result = await self.db.execute(stmt)
        return int(result.scalar() or 0)

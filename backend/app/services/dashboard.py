from __future__ import annotations

import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db import ReportResult
from app.schemas.dashboard import DashboardStatsResponse

logger = logging.getLogger(__name__)


class DashboardService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_stats(self) -> DashboardStatsResponse:
        try:
            result = await self.db.execute(select(ReportResult))
            rows = result.scalars().all()
        except Exception as exc:
            logger.exception("Failed to compute dashboard stats", exc_info=exc)
            raise
        total = len(rows)
        urgent = sum(1 for r in rows if r.triage.get("urgency_score", 0) >= 0.6)
        avg = round(sum(r.triage.get("urgency_score", 0) for r in rows) / total, 4) if total else 0.0
        conditions: dict[str, int] = {}
        for r in rows:
            label = r.classification.get("disease", "unknown")
            conditions[label] = conditions.get(label, 0) + 1
        top = sorted(conditions.items(), key=lambda x: x[1], reverse=True)[:5]
        top_conditions = [(name, round(count / total, 4)) for name, count in top] if total else []
        return DashboardStatsResponse(
            total_reports=total,
            urgent_count=urgent,
            avg_urgency_score=avg,
            top_conditions=top_conditions,
        )

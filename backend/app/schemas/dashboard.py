from __future__ import annotations

from pydantic import BaseModel


class DashboardStatsResponse(BaseModel):
    total_reports: int
    urgent_count: int
    avg_urgency_score: float
    top_conditions: list[tuple[str, float]]

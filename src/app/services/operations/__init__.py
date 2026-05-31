"""
Operations and dashboard summary service.
"""

from datetime import UTC, datetime
from typing import Dict

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.analysis import AnalysisReport
from app.models.cost import CostRecord
from app.models.hotspot import HotspotItem
from app.models.review import ReviewRecord
from app.models.script import Script
from app.models.video import VideoTask


class OperationsService:
    """Aggregate simple operational metrics for MVP delivery."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def build_summary(self) -> Dict[str, object]:
        hotspot_count = await self._count_rows(HotspotItem)
        analysis_count = await self._count_rows(AnalysisReport)
        script_count = await self._count_rows(Script)
        video_count = await self._count_rows(VideoTask)
        review_count = await self._count_rows(ReviewRecord)
        cost_record_count = await self._count_rows(CostRecord)

        script_status = await self._count_by_status(Script)
        video_status = await self._count_by_status(VideoTask)
        cost_breakdown = await self._sum_costs()
        total_cost = round(sum(cost_breakdown.values()), 4)
        budget_usage_ratio = round(
            total_cost / settings.DAILY_BUDGET if settings.DAILY_BUDGET else 0.0,
            4,
        )

        return {
            "counts": {
                "hotspots": hotspot_count,
                "analyses": analysis_count,
                "scripts": script_count,
                "videos": video_count,
                "reviews": review_count,
                "cost_records": cost_record_count,
            },
            "script_status": script_status,
            "video_status": video_status,
            "cost_breakdown": cost_breakdown,
            "daily_budget": settings.DAILY_BUDGET,
            "budget_usage_ratio": budget_usage_ratio,
            "generated_at": datetime.now(UTC),
        }

    async def _count_rows(self, model) -> int:
        result = await self.session.execute(select(func.count()).select_from(model))
        return int(result.scalar_one() or 0)

    async def _count_by_status(self, model) -> Dict[str, int]:
        result = await self.session.execute(
            select(model.status, func.count()).group_by(model.status)
        )
        return {status or "unknown": int(count) for status, count in result.all()}

    async def _sum_costs(self) -> Dict[str, float]:
        analysis_cost = await self._sum_cost(AnalysisReport)
        script_cost = await self._sum_cost(Script)
        video_cost = await self._sum_cost(VideoTask)
        return {
            "analysis": analysis_cost,
            "script": script_cost,
            "video": video_cost,
            "total": round(analysis_cost + script_cost + video_cost, 4),
        }

    async def _sum_cost(self, model) -> float:
        result = await self.session.execute(select(func.sum(model.api_cost)))
        value = result.scalar_one()
        return round(float(value or 0.0), 4)

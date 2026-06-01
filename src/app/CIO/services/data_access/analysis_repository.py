from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.CIO.models.analysis import AnalysisReport


class AnalysisRepository:
    """Centralized repository for CIO-owned analysis persistence and querying."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, payload: dict[str, Any]) -> AnalysisReport:
        report = AnalysisReport(**payload)
        self.session.add(report)
        await self.session.flush()
        return report

    async def get_by_uuid(self, analysis_id: str) -> AnalysisReport | None:
        result = await self.session.execute(select(AnalysisReport).where(AnalysisReport.uuid == analysis_id))
        return result.scalar_one_or_none()

    async def list_by_hotspot(self, hotspot_id: str, *, limit: int = 50) -> list[AnalysisReport]:
        query = (
            select(AnalysisReport)
            .where(AnalysisReport.hotspot_id == hotspot_id)
            .order_by(AnalysisReport.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

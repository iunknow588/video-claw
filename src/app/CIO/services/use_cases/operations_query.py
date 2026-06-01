from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.CIO.models.cost import CostRecord
from app.CIO.models.review import ReviewRecord
from app.CIO.services.operations import OperationsService
from app.CIO.services.storage import describe_video_storage


class OperationsQueryUseCase:
    """API-facing operations query use case owned by CIO."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.service = OperationsService(session)

    async def build_summary(self) -> dict[str, Any]:
        return await self.service.build_summary()

    async def list_reviews(self, *, item_type: str | None, limit: int) -> list[ReviewRecord]:
        query = select(ReviewRecord).order_by(ReviewRecord.created_at.desc()).limit(limit)
        if item_type:
            query = query.where(ReviewRecord.item_type == item_type)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_costs(self, *, source_type: str | None, limit: int) -> list[CostRecord]:
        query = select(CostRecord).order_by(CostRecord.created_at.desc()).limit(limit)
        if source_type:
            query = query.where(CostRecord.source_type == source_type)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    def get_storage_status(self) -> dict[str, Any]:
        return describe_video_storage()

from __future__ import annotations

from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from departments.CIO.models.knowledge_asset import KnowledgeAsset


class KnowledgeRepository:
    """Centralized repository for CIO knowledge assets."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_assets(self, *, category: str | None = None) -> list[KnowledgeAsset]:
        query = select(KnowledgeAsset).order_by(KnowledgeAsset.category.asc(), KnowledgeAsset.created_at.asc())
        if category:
            query = query.where(KnowledgeAsset.category == category)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_category_key(self, *, category: str, asset_key: str) -> KnowledgeAsset | None:
        result = await self.session.execute(
            select(KnowledgeAsset).where(KnowledgeAsset.category == category, KnowledgeAsset.asset_key == asset_key)
        )
        return result.scalar_one_or_none()

    async def create_asset(self, payload: dict[str, Any]) -> KnowledgeAsset:
        record = KnowledgeAsset(**jsonable_encoder(payload))
        self.session.add(record)
        await self.session.flush()
        return record

    async def update_asset(self, record: KnowledgeAsset, payload: dict[str, Any]) -> KnowledgeAsset:
        for key, value in jsonable_encoder(payload).items():
            setattr(record, key, value)
        await self.session.flush()
        return record

    async def count_assets(self) -> int:
        result = await self.session.execute(select(func.count()).select_from(KnowledgeAsset))
        return int(result.scalar_one() or 0)

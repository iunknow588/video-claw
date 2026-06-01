from __future__ import annotations

from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.CIO.models.hotspot import HotspotItem


class HotspotRepository:
    """Centralized repository for CIO-owned hotspot persistence and querying."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, payload: dict[str, Any]) -> HotspotItem:
        item = HotspotItem(**payload)
        self.session.add(item)
        await self.session.flush()
        return item

    async def get_by_uuid(self, hotspot_id: str) -> HotspotItem | None:
        result = await self.session.execute(select(HotspotItem).where(HotspotItem.uuid == hotspot_id))
        return result.scalar_one_or_none()

    async def get_by_platform_content(self, platform: str, content_id: str) -> HotspotItem | None:
        result = await self.session.execute(
            select(HotspotItem).where(and_(HotspotItem.platform == platform, HotspotItem.content_id == content_id))
        )
        return result.scalar_one_or_none()

    async def list_recent(self, *, platform: str | None = None, limit: int = 50) -> list[HotspotItem]:
        query = select(HotspotItem).order_by(HotspotItem.created_at.desc()).limit(limit)
        if platform:
            query = query.where(HotspotItem.platform == platform)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def search(self, *, keyword: str, platform: str | None = None, limit: int = 50) -> list[HotspotItem]:
        pattern = f"%{keyword}%"
        query = (
            select(HotspotItem)
            .where(
                or_(
                    HotspotItem.title.ilike(pattern),
                    HotspotItem.author.ilike(pattern),
                    HotspotItem.category.ilike(pattern),
                    HotspotItem.content_id.ilike(pattern),
                )
            )
            .order_by(HotspotItem.created_at.desc())
            .limit(limit)
        )
        if platform:
            query = query.where(HotspotItem.platform == platform)
        result = await self.session.execute(query)
        return list(result.scalars().all())

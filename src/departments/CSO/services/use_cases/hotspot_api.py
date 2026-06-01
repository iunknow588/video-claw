from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from departments.CIO.models.hotspot import HotspotItem
from departments.CIO.schemas.video import HotspotCreate, HotspotFetchRequest
from departments.CSO.services.hotspot import HotspotService


class HotspotApiUseCase:
    """API-facing hotspot use case owned by CSO."""

    def __init__(self, session: AsyncSession):
        self.service = HotspotService(session)

    async def create_hotspot(self, data: HotspotCreate) -> HotspotItem:
        existing = await self.service.get_by_platform_id(data.platform, data.content_id)
        if existing:
            raise ValueError("Hotspot already exists")
        return await self.service.create(data)

    async def list_hotspots(self, *, platform: str | None, limit: int) -> list[HotspotItem]:
        return await self.service.list_recent(platform=platform, limit=limit)

    async def search_hotspots(
        self,
        *,
        keyword: str,
        platform: str | None,
        limit: int,
    ) -> dict[str, object]:
        results = await self.service.search(keyword=keyword, platform=platform, limit=limit)
        return {"keyword": keyword, "platform": platform, "results": results}

    async def fetch_hotspots(self, request: HotspotFetchRequest) -> list[HotspotItem]:
        return await self.service.fetch_hotspots(request)

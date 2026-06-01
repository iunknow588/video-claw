"""
Hotspot Collection Service
"""

from typing import List, Optional

from app.CEO.core.logging import get_logger
from app.CIO.models.hotspot import HotspotItem
from app.CIO.schemas.video import HotspotCreate, HotspotFetchRequest
from app.CIO.services.data_access.hotspot_repository import HotspotRepository
from app.CSO.services.hotspot_providers import get_hotspot_provider

logger = get_logger(__name__)


class HotspotService:
    """Service for collecting and managing hotspot content."""

    def __init__(self, session):
        self.repository = HotspotRepository(session)

    async def create(self, data: HotspotCreate) -> HotspotItem:
        item = await self.repository.create(data.model_dump())
        logger.info("Hotspot created", uuid=item.uuid, platform=item.platform)
        return item

    async def get_by_platform_id(self, platform: str, content_id: str) -> Optional[HotspotItem]:
        return await self.repository.get_by_platform_content(platform, content_id)

    async def list_recent(self, platform: Optional[str] = None, limit: int = 50) -> List[HotspotItem]:
        return await self.repository.list_recent(platform=platform, limit=limit)

    async def search(self, keyword: str, platform: Optional[str] = None, limit: int = 50) -> List[HotspotItem]:
        return await self.repository.search(keyword=keyword, platform=platform, limit=limit)

    async def fetch_hotspots(self, request: HotspotFetchRequest) -> List[HotspotItem]:
        platform = request.platform.lower()
        payloads = await self._fetch_from_provider(platform, request.keyword, request.count)

        created_items: List[HotspotItem] = []
        for payload in payloads:
            existing = await self.get_by_platform_id(platform, payload["content_id"])
            if existing:
                created_items.append(existing)
                continue
            item = await self.create(HotspotCreate(**payload))
            created_items.append(item)
        return created_items

    async def fetch_from_douyin(self, keyword: str, count: int = 20) -> List[dict]:
        logger.info("Fetching Douyin hotspots", keyword=keyword, count=count)
        return await self._fetch_from_provider("douyin", keyword, count)

    async def fetch_from_xiaohongshu(self, keyword: str, count: int = 20) -> List[dict]:
        logger.info("Fetching XHS hotspots", keyword=keyword, count=count)
        return await self._fetch_from_provider("xiaohongshu", keyword, count)

    async def fetch_from_bilibili(self, keyword: str, count: int = 20) -> List[dict]:
        logger.info("Fetching Bilibili hotspots", keyword=keyword, count=count)
        return await self._fetch_from_provider("bilibili", keyword, count)

    async def _fetch_from_provider(self, platform: str, keyword: str, count: int) -> List[dict]:
        provider = get_hotspot_provider(platform)
        return await provider.fetch(keyword=keyword, count=count)

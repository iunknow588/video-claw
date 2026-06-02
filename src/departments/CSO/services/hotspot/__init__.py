"""
Hotspot Collection Service
"""

from typing import Any, List, Optional

from departments.CEO.core.logging import get_logger
from departments.CIO.models.hotspot import HotspotItem
from departments.CIO.schemas.video import HotspotCreate, HotspotFetchRequest
from departments.CIO.services.data_access.hotspot_repository import HotspotRepository
from departments.CSO.services.hotspot_providers import get_hotspot_provider

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
                self._sync_existing_item(existing, payload)
                await self.repository.session.flush()
                await self.repository.session.refresh(existing)
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

    async def fetch_from_xigua(self, keyword: str, count: int = 20) -> List[dict]:
        logger.info("Fetching Xigua hotspots", keyword=keyword, count=count)
        return await self._fetch_from_provider("xigua", keyword, count)

    async def fetch_from_bilibili(self, keyword: str, count: int = 20) -> List[dict]:
        logger.info("Fetching Bilibili hotspots", keyword=keyword, count=count)
        return await self._fetch_from_provider("bilibili", keyword, count)

    async def _fetch_from_provider(self, platform: str, keyword: str, count: int) -> List[dict]:
        provider = get_hotspot_provider(platform)
        return await provider.fetch(keyword=keyword, count=count)

    @staticmethod
    def _sync_existing_item(item: HotspotItem, payload: dict[str, Any]) -> None:
        for field in (
            "title",
            "author",
            "author_id",
            "url",
            "cover_image",
            "video_url",
            "view_count",
            "like_count",
            "comment_count",
            "share_count",
            "category",
            "tags",
            "duration",
            "fetched_at",
        ):
            if field in payload:
                setattr(item, field, payload[field])

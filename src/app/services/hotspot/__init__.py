"""
Hotspot Collection Service
"""

from typing import List, Optional

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.hotspot import HotspotItem
from app.schemas.video import HotspotCreate, HotspotFetchRequest
from app.services.hotspot_providers import get_hotspot_provider

logger = get_logger(__name__)


class HotspotService:
    """Service for collecting and managing hotspot content."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: HotspotCreate) -> HotspotItem:
        """Create new hotspot item."""
        item = HotspotItem(**data.model_dump())
        self.session.add(item)
        await self.session.flush()
        logger.info("Hotspot created", uuid=item.uuid, platform=item.platform)
        return item

    async def get_by_platform_id(self, platform: str, content_id: str) -> Optional[HotspotItem]:
        """Get hotspot by platform and content ID."""
        result = await self.session.execute(
            select(HotspotItem).where(
                and_(HotspotItem.platform == platform, HotspotItem.content_id == content_id)
            )
        )
        return result.scalar_one_or_none()

    async def list_recent(self, platform: Optional[str] = None, limit: int = 50) -> List[HotspotItem]:
        """List recent hotspots."""
        query = select(HotspotItem).order_by(HotspotItem.created_at.desc()).limit(limit)
        if platform:
            query = query.where(HotspotItem.platform == platform)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def search(self, keyword: str, platform: Optional[str] = None, limit: int = 50) -> List[HotspotItem]:
        """Search hotspots by title, author, category, or content_id."""
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
        return result.scalars().all()

    async def fetch_hotspots(self, request: HotspotFetchRequest) -> List[HotspotItem]:
        """Fetch hotspots from the selected provider and persist new items."""
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
        """Fetch hotspot from Douyin through its provider adapter."""
        logger.info("Fetching Douyin hotspots", keyword=keyword, count=count)
        return await self._fetch_from_provider("douyin", keyword, count)

    async def fetch_from_xiaohongshu(self, keyword: str, count: int = 20) -> List[dict]:
        """Fetch hotspot from Xiaohongshu through its provider adapter."""
        logger.info("Fetching XHS hotspots", keyword=keyword, count=count)
        return await self._fetch_from_provider("xiaohongshu", keyword, count)

    async def fetch_from_bilibili(self, keyword: str, count: int = 20) -> List[dict]:
        """Fetch hotspot from Bilibili through its provider adapter."""
        logger.info("Fetching Bilibili hotspots", keyword=keyword, count=count)
        return await self._fetch_from_provider("bilibili", keyword, count)

    async def _fetch_from_provider(self, platform: str, keyword: str, count: int) -> List[dict]:
        provider = get_hotspot_provider(platform)
        return await provider.fetch(keyword=keyword, count=count)

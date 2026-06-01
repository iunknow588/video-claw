"""
Hotspot provider adapter skeletons.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List


class BaseHotspotProvider(ABC):
    """Base adapter interface for platform hotspot providers."""

    platform: str = ""

    @abstractmethod
    async def fetch(self, *, keyword: str, count: int) -> List[dict]:
        """Fetch hotspot payloads for a keyword."""


class MockHotspotProvider(BaseHotspotProvider):
    """Default placeholder provider for MVP and local workflow tests."""

    def __init__(self, platform: str):
        self.platform = platform

    async def fetch(self, *, keyword: str, count: int) -> List[dict]:
        safe_keyword = keyword.strip() or "hot-topic"
        return [
            {
                "platform": self.platform,
                "content_id": f"{self.platform}-{safe_keyword}-{index + 1}",
                "title": f"{safe_keyword} 热门拆解 {index + 1}",
                "author": f"{self.platform}_creator_{index + 1}",
                "author_id": f"{self.platform}_author_{index + 1}",
                "url": f"https://example.com/{self.platform}/{safe_keyword}/{index + 1}",
                "cover_image": f"https://example.com/assets/{self.platform}/{index + 1}.jpg",
                "video_url": None,
                "view_count": 10000 + index * 1500,
                "like_count": 1000 + index * 120,
                "comment_count": 100 + index * 10,
                "share_count": 50 + index * 5,
                "category": "general",
                "tags": [safe_keyword, self.platform, "mvp"],
                "duration": 30 + index,
                "fetched_at": None,
            }
            for index in range(count)
        ]


class DouyinHotspotProvider(MockHotspotProvider):
    platform = "douyin"

    def __init__(self):
        super().__init__(self.platform)


class XiaohongshuHotspotProvider(MockHotspotProvider):
    platform = "xiaohongshu"

    def __init__(self):
        super().__init__(self.platform)


class BilibiliHotspotProvider(MockHotspotProvider):
    platform = "bilibili"

    def __init__(self):
        super().__init__(self.platform)


def get_hotspot_provider(platform: str) -> BaseHotspotProvider:
    normalized = platform.lower()
    providers = {
        "douyin": DouyinHotspotProvider(),
        "xiaohongshu": XiaohongshuHotspotProvider(),
        "bilibili": BilibiliHotspotProvider(),
    }
    try:
        return providers[normalized]
    except KeyError as exc:
        raise ValueError(f"Unsupported platform: {platform}") from exc

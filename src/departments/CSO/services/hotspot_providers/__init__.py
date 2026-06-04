"""
Hotspot provider adapters.
"""

from __future__ import annotations

import os
import re
import hashlib
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from html import unescape
from typing import Any, List
from urllib.parse import urlencode

import httpx


DEFAULT_TIMEOUT = 20.0


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean_html_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    text = re.sub(r"<[^>]+>", "", unescape(value))
    return " ".join(text.split())


def _normalize_text(value: Any, *, limit: int = 160) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.strip().split())[:limit]


def _parse_count(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return max(value, 0)
    if isinstance(value, float):
        return max(int(value), 0)
    if not isinstance(value, str):
        return 0

    text = value.strip().lower().replace(",", "")
    if not text:
        return 0
    text = text.replace("次播放", "").replace("播放", "").replace("点赞", "").replace("评论", "").replace("收藏", "")
    multiplier = 1
    if text.endswith("w"):
        multiplier = 10000
        text = text[:-1]
    elif text.endswith("万"):
        multiplier = 10000
        text = text[:-1]
    elif text.endswith("k"):
        multiplier = 1000
        text = text[:-1]

    try:
        return max(int(float(text) * multiplier), 0)
    except ValueError:
        digits = re.findall(r"\d+", text)
        return int(digits[0]) if digits else 0


def _pick_first(*values: Any) -> str:
    for value in values:
        if isinstance(value, str):
            normalized = _normalize_text(value)
            if normalized:
                return normalized
    return ""


def _pick_nested(mapping: dict[str, Any], *paths: tuple[str, ...]) -> Any:
    for path in paths:
        current: Any = mapping
        matched = True
        for part in path:
            if isinstance(current, dict):
                if part not in current:
                    matched = False
                    break
                current = current[part]
                continue
            if isinstance(current, list):
                if not part.isdigit():
                    matched = False
                    break
                index = int(part)
                if index < 0 or index >= len(current):
                    matched = False
                    break
                current = current[index]
                continue
            matched = False
            break
        if matched:
            return current
    return None


def _normalize_url(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    if value.startswith("//"):
        return f"https:{value}"
    return value


class BaseHotspotProvider(ABC):
    """Base adapter interface for platform hotspot providers."""

    platform: str = ""

    @abstractmethod
    async def fetch(self, *, keyword: str, count: int) -> List[dict]:
        """Fetch hotspot payloads for a keyword."""


class MockHotspotProvider(BaseHotspotProvider):
    """Explicit placeholder provider for tests only."""

    def __init__(self, platform: str):
        self.platform = platform

    async def fetch(self, *, keyword: str, count: int) -> List[dict]:
        safe_keyword = keyword.strip() or "hot-topic"
        fetched_at = _utc_now_iso()
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
                "tags": [safe_keyword, self.platform, "mvp", "mock"],
                "duration": 30 + index,
                "fetched_at": fetched_at,
            }
            for index in range(count)
        ]


class BilibiliHotspotProvider(BaseHotspotProvider):
    platform = "bilibili"
    NAV_API = "https://api.bilibili.com/x/web-interface/nav"
    SEARCH_API = "https://api.bilibili.com/x/web-interface/wbi/search/type"
    WBI_MIXIN_KEY = [
        46, 47, 18, 2, 53, 8, 23, 32,
        15, 50, 10, 31, 58, 3, 45, 35,
        27, 43, 5, 49, 33, 9, 42, 19,
        29, 28, 14, 39, 12, 38, 41, 13,
        37, 48, 7, 16, 24, 55, 40, 61,
        26, 17, 0, 1, 60, 51, 30, 4,
        22, 25, 54, 21, 56, 59, 6, 63,
        57, 62, 11, 36, 20, 34, 44, 52,
    ]

    async def fetch(self, *, keyword: str, count: int) -> List[dict]:
        async with httpx.AsyncClient(
            headers={"user-agent": "Mozilla/5.0"},
            timeout=DEFAULT_TIMEOUT,
            follow_redirects=True,
        ) as client:
            params = await self._build_signed_params(client, keyword=keyword, count=count)
            response = await client.get(self.SEARCH_API, params=params)
            response.raise_for_status()
            payload = response.json()

        if int(payload.get("code", -1)) != 0:
            raise ValueError(f"B站检索失败：{payload.get('message') or payload.get('msg') or '未知错误'}")

        results = payload.get("data", {}).get("result") or []
        normalized: list[dict[str, Any]] = []
        fetched_at = _utc_now_iso()
        for item in results[:count]:
            if not isinstance(item, dict):
                continue
            bvid = _pick_first(item.get("bvid"))
            aid = str(item.get("aid") or item.get("id") or "").strip()
            content_id = bvid or aid
            if not content_id:
                continue
            normalized.append(
                {
                    "platform": self.platform,
                    "content_id": content_id,
                    "title": _clean_html_text(item.get("title")) or _pick_first(item.get("description")) or keyword,
                    "author": _pick_first(item.get("author")),
                    "author_id": str(item.get("mid") or "").strip(),
                    "url": _normalize_url(_pick_first(item.get("arcurl"))).replace("http://", "https://"),
                    "cover_image": _normalize_url(_pick_first(item.get("pic"))),
                    "video_url": None,
                    "view_count": _parse_count(item.get("play")),
                    "like_count": _parse_count(item.get("favorites")),
                    "comment_count": _parse_count(item.get("video_review") or item.get("review")),
                    "share_count": 0,
                    "category": _pick_first(item.get("typename")),
                    "tags": [tag for tag in _split_csv(item.get("tag"))[:8]],
                    "duration": _parse_duration(item.get("duration")),
                    "fetched_at": fetched_at,
                }
            )
        return normalized

    async def _build_signed_params(
        self,
        client: httpx.AsyncClient,
        *,
        keyword: str,
        count: int,
    ) -> dict[str, Any]:
        nav_response = await client.get(self.NAV_API)
        nav_response.raise_for_status()
        nav_payload = nav_response.json()
        wbi_img = nav_payload.get("data", {}).get("wbi_img") or {}
        img_key = str(wbi_img.get("img_url", "")).rsplit("/", 1)[-1].split(".")[0]
        sub_key = str(wbi_img.get("sub_url", "")).rsplit("/", 1)[-1].split(".")[0]
        mixin_key = self._get_mixin_key(img_key + sub_key)
        params = {
            "search_type": "video",
            "keyword": keyword,
            "page": 1,
            "page_size": max(1, min(count, 20)),
            "wts": int(datetime.now(timezone.utc).timestamp()),
        }
        cleaned = {
            key: re.sub(r"[!'()*]", "", str(value))
            for key, value in sorted(params.items())
        }
        query = urlencode(cleaned)
        cleaned["w_rid"] = hashlib.md5(f"{query}{mixin_key}".encode("utf-8")).hexdigest()
        return cleaned

    def _get_mixin_key(self, origin_key: str) -> str:
        mixed = "".join(origin_key[index] for index in self.WBI_MIXIN_KEY if index < len(origin_key))
        return mixed[:32]


class XiaohongshuHotspotProvider(BaseHotspotProvider):
    platform = "xiaohongshu"
    SEARCH_PAGE = "https://www.xiaohongshu.com/search_result/"
    SEARCH_API = "https://edith.xiaohongshu.com/api/sns/web/v1/search/notes"
    COOKIE_ENV = "XIAOHONGSHU_COOKIE"

    async def fetch(self, *, keyword: str, count: int) -> List[dict]:
        cookie = os.environ.get(self.COOKIE_ENV, "").strip()
        if not cookie:
            raise ValueError("小红书真实检索需要先在环境变量中配置 XIAOHONGSHU_COOKIE。")

        headers = {
            "user-agent": "Mozilla/5.0",
            "origin": "https://www.xiaohongshu.com",
            "referer": f"{self.SEARCH_PAGE}?keyword={keyword}",
            "cookie": cookie,
            "content-type": "application/json;charset=UTF-8",
        }
        payload = {
            "keyword": keyword,
            "page": 1,
            "page_size": max(1, min(count, 20)),
            "search_id": "",
            "sort": "general",
            "note_type": 0,
            "ext_flags": [],
            "filters": [],
        }

        async with httpx.AsyncClient(headers=headers, timeout=DEFAULT_TIMEOUT, follow_redirects=True) as client:
            await client.get(self.SEARCH_PAGE, params={"keyword": keyword})
            response = await client.post(self.SEARCH_API, json=payload)
            response.raise_for_status()
            body = response.json()

        if not body.get("success", False):
            raise ValueError(f"小红书真实检索失败：{body.get('msg') or body.get('message') or '未知错误'}")

        items = body.get("data", {}).get("items") or []
        normalized: list[dict[str, Any]] = []
        fetched_at = _utc_now_iso()

        for item in items[:count]:
            if not isinstance(item, dict):
                continue
            note_card = item.get("note_card") if isinstance(item.get("note_card"), dict) else item
            if not isinstance(note_card, dict):
                continue
            note_id = _pick_first(
                note_card.get("note_id"),
                note_card.get("id"),
                item.get("id"),
            )
            if not note_id:
                continue
            user_info = note_card.get("user") if isinstance(note_card.get("user"), dict) else {}
            interact_info = note_card.get("interact_info") if isinstance(note_card.get("interact_info"), dict) else {}
            xsec_token = _pick_first(note_card.get("xsec_token"), item.get("xsec_token"))
            cover_image = _pick_first(
                _pick_nested(note_card, ("cover", "url_pre")),
                _pick_nested(note_card, ("cover", "url_default")),
                _pick_nested(note_card, ("image_list", "0", "url_default")),
            )
            normalized.append(
                {
                    "platform": self.platform,
                    "content_id": note_id,
                    "title": _pick_first(note_card.get("display_title"), note_card.get("title"), keyword),
                    "author": _pick_first(user_info.get("nickname"), user_info.get("nick_name"), user_info.get("name")),
                    "author_id": _pick_first(user_info.get("user_id"), user_info.get("userid")),
                    "url": self._build_note_url(note_id=note_id, xsec_token=xsec_token),
                    "cover_image": _normalize_url(cover_image),
                    "video_url": None,
                    "view_count": _parse_count(interact_info.get("view_count")),
                    "like_count": _parse_count(interact_info.get("liked_count")),
                    "comment_count": _parse_count(interact_info.get("comment_count")),
                    "share_count": _parse_count(interact_info.get("share_count")),
                    "category": _pick_first(note_card.get("type"), note_card.get("note_type")),
                    "tags": _normalize_tag_list(note_card.get("tag_list")),
                    "duration": _parse_count(note_card.get("video_duration")),
                    "fetched_at": fetched_at,
                }
            )
        return normalized

    @staticmethod
    def _build_note_url(*, note_id: str, xsec_token: str) -> str:
        if xsec_token:
            return f"https://www.xiaohongshu.com/explore/{note_id}?xsec_token={xsec_token}&xsec_source=pc_search"
        return f"https://www.xiaohongshu.com/explore/{note_id}"


class DouyinHotspotProvider(BaseHotspotProvider):
    platform = "douyin"
    SEARCH_API = "https://www.douyin.com/aweme/v1/web/general/search/single/"
    COOKIE_ENV = "DOUYIN_COOKIE"

    async def fetch(self, *, keyword: str, count: int) -> List[dict]:
        cookie = os.environ.get(self.COOKIE_ENV, "").strip()
        if not cookie:
            raise ValueError("抖音真实检索需要先在环境变量中配置 DOUYIN_COOKIE。")

        headers = {
            "user-agent": "Mozilla/5.0",
            "referer": "https://www.douyin.com/",
            "cookie": cookie,
        }
        params = {
            "device_platform": "webapp",
            "aid": "6383",
            "channel": "channel_pc_web",
            "search_channel": "aweme_general",
            "keyword": keyword,
            "offset": "0",
            "count": str(max(1, min(count, 20))),
        }
        async with httpx.AsyncClient(headers=headers, timeout=DEFAULT_TIMEOUT, follow_redirects=True) as client:
            response = await client.get(self.SEARCH_API, params=params)
            response.raise_for_status()
            body = response.json()

        if int(body.get("status_code") or 0) != 0:
            raise ValueError(f"抖音真实检索失败：{body.get('status_msg') or body.get('message') or '未知错误'}")

        results = body.get("data") or []
        normalized: list[dict[str, Any]] = []
        fetched_at = _utc_now_iso()
        for item in results[:count]:
            if not isinstance(item, dict):
                continue
            aweme = item.get("aweme_info") if isinstance(item.get("aweme_info"), dict) else {}
            if not aweme and isinstance(item.get("aweme_mix_info"), dict):
                mix_items = item["aweme_mix_info"].get("mix_items") or []
                if mix_items and isinstance(mix_items[0], dict):
                    aweme = mix_items[0]
            if not aweme:
                continue
            aweme_id = _pick_first(aweme.get("aweme_id"))
            if not aweme_id:
                continue
            author = aweme.get("author") if isinstance(aweme.get("author"), dict) else {}
            statistics = aweme.get("statistics") if isinstance(aweme.get("statistics"), dict) else {}
            video = aweme.get("video") if isinstance(aweme.get("video"), dict) else {}
            cover = video.get("cover") if isinstance(video.get("cover"), dict) else {}
            cover_list = cover.get("url_list") if isinstance(cover.get("url_list"), list) else []
            normalized.append(
                {
                    "platform": self.platform,
                    "content_id": aweme_id,
                    "title": _pick_first(aweme.get("desc"), keyword),
                    "author": _pick_first(author.get("nickname")),
                    "author_id": _pick_first(author.get("sec_uid"), author.get("uid")),
                    "url": f"https://www.douyin.com/video/{aweme_id}",
                    "cover_image": _normalize_url(cover_list[0] if cover_list else ""),
                    "video_url": None,
                    "view_count": _parse_count(statistics.get("play_count")),
                    "like_count": _parse_count(statistics.get("digg_count")),
                    "comment_count": _parse_count(statistics.get("comment_count")),
                    "share_count": _parse_count(statistics.get("share_count")),
                    "category": "video",
                    "tags": _extract_douyin_tags(aweme),
                    "duration": _parse_count(aweme.get("duration")) // 1000,
                    "fetched_at": fetched_at,
                }
            )
        return normalized


class XiguaHotspotProvider(BaseHotspotProvider):
    platform = "xigua"

    async def fetch(self, *, keyword: str, count: int) -> List[dict]:
        raise ValueError("西瓜视频暂未接入稳定的公开真实检索接口，请优先使用 B站 / 小红书 / 抖音。")


def get_hotspot_provider(platform: str) -> BaseHotspotProvider:
    normalized = platform.lower()
    use_mock = os.environ.get("HOTSPOT_PROVIDER_MODE", "real").strip().lower() == "mock"
    if use_mock:
        return MockHotspotProvider(normalized)

    providers = {
        "douyin": DouyinHotspotProvider(),
        "xiaohongshu": XiaohongshuHotspotProvider(),
        "xigua": XiguaHotspotProvider(),
        "bilibili": BilibiliHotspotProvider(),
    }
    try:
        return providers[normalized]
    except KeyError as exc:
        raise ValueError(f"Unsupported platform: {platform}") from exc


def _normalize_tag_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    tags: list[str] = []
    for item in value[:8]:
        if isinstance(item, str):
            normalized = _normalize_text(item, limit=40)
            if normalized:
                tags.append(normalized)
        elif isinstance(item, dict):
            normalized = _pick_first(item.get("name"), item.get("tag"))
            if normalized:
                tags.append(normalized)
    return tags


def _extract_douyin_tags(aweme: dict[str, Any]) -> list[str]:
    text_extra = aweme.get("text_extra") if isinstance(aweme.get("text_extra"), list) else []
    tags: list[str] = []
    for item in text_extra[:8]:
        if not isinstance(item, dict):
            continue
        tag_name = _pick_first(item.get("hashtag_name"), item.get("tag_name"))
        if tag_name:
            tags.append(tag_name)
    return tags


def _split_csv(value: Any) -> list[str]:
    if not isinstance(value, str):
        return []
    return [token.strip() for token in value.split(",") if token.strip()]


def _parse_duration(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if not isinstance(value, str):
        return 0
    parts = [part for part in value.split(":") if part.isdigit()]
    if not parts:
        return 0
    total = 0
    for part in parts:
        total = total * 60 + int(part)
    return total

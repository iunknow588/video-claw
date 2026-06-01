"""
Domain-driven hotspot ranking and prompt package building.
"""

from __future__ import annotations

from collections import Counter
import re
from typing import Any, Iterable, List

from departments.CIO.models.analysis import AnalysisReport
from departments.CIO.models.hotspot import HotspotItem


class TrendIntelligenceService:
    """Transforms hotspots and analysis output into reusable prompt packages."""

    def expand_domain_queries(
        self,
        *,
        domain: str,
        audience: str | None = None,
        publish_goal: str | None = None,
    ) -> List[str]:
        base_queries = [
            domain,
            f"{domain} 爆款",
            f"{domain} 热门",
            f"{domain} 选题",
        ]
        if audience:
            base_queries.append(f"{domain} {audience}")
        if publish_goal:
            base_queries.append(f"{domain} {publish_goal}")

        unique_queries: list[str] = []
        seen: set[str] = set()
        for item in base_queries:
            normalized = item.strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                unique_queries.append(normalized)
        return unique_queries

    def rank_hotspots(self, hotspots: Iterable[HotspotItem]) -> List[dict[str, Any]]:
        ranked: list[dict[str, Any]] = []
        for item in hotspots:
            heat_score = self._calculate_heat_score(item)
            ranked.append({"hotspot": item, "heat_score": heat_score})
        ranked.sort(key=lambda x: x["heat_score"], reverse=True)
        return ranked

    def build_prompt_package(
        self,
        *,
        domain: str,
        hotspots: List[HotspotItem],
        analyses: List[AnalysisReport],
        style: str,
        content_type: str,
        audience: str | None = None,
        publish_goal: str | None = None,
    ) -> dict[str, Any]:
        token_counter: Counter[str] = Counter()
        for hotspot in hotspots:
            token_counter.update(self._extract_hotspot_tokens(hotspot))
        for report in analyses:
            token_counter.update(self._extract_analysis_tokens(report))
        token_counter.update([domain])
        if audience:
            token_counter.update([audience])
        if publish_goal:
            token_counter.update([publish_goal])

        core_keywords = [token for token, _ in token_counter.most_common(8)]
        hook_keywords = self._select_hook_keywords(core_keywords)
        visual_keywords = self._build_visual_keywords(style=style, content_type=content_type)
        title_candidates = self._build_title_candidates(domain=domain, hook_keywords=hook_keywords)

        prompt_summary = (
            f"围绕“{domain}”领域，参考当前高热度短视频的结构、关键词和钩子句，"
            f"输出更适合 {content_type} 类型内容的短视频方案。"
        )
        script_topic = " / ".join(title_candidates[:2]) if title_candidates else domain
        video_prompt = (
            f"主题：{domain}；核心关键词：{', '.join(core_keywords[:6])}；"
            f"开头钩子：{', '.join(hook_keywords[:3])}；"
            f"视觉风格：{', '.join(visual_keywords)}。"
        )

        return {
            "core_keywords": core_keywords,
            "hook_keywords": hook_keywords,
            "visual_keywords": visual_keywords,
            "title_candidates": title_candidates,
            "prompt_summary": prompt_summary,
            "script_topic": script_topic,
            "video_prompt": video_prompt,
        }

    def _calculate_heat_score(self, hotspot: HotspotItem) -> int:
        return (
            int(hotspot.view_count or 0)
            + int(hotspot.like_count or 0) * 8
            + int(hotspot.comment_count or 0) * 15
            + int(hotspot.share_count or 0) * 20
        )

    def _extract_hotspot_tokens(self, hotspot: HotspotItem) -> list[str]:
        fields = [
            hotspot.title or "",
            hotspot.category or "",
            hotspot.author or "",
            " ".join(hotspot.tags or []),
        ]
        return self._normalize_tokens(self._tokenize(" ".join(fields)))

    def _extract_analysis_tokens(self, report: AnalysisReport) -> list[str]:
        reusable = " ".join(str(item) for item in (report.reusable_elements or []))
        summary = report.framework_summary or ""
        risks = " ".join(str(item) for item in (report.risk_warnings or []))
        return self._normalize_tokens(self._tokenize(f"{summary} {reusable} {risks}"))

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"[\u4e00-\u9fffA-Za-z0-9]+", text)

    def _normalize_tokens(self, tokens: Iterable[str]) -> list[str]:
        skip_words = {
            "mvp",
            "creator",
            "general",
            "copyright",
            "check",
            "required",
            "video",
            "content",
            "CCO",
        }
        normalized: list[str] = []
        for token in tokens:
            clean = token.strip().lower()
            if not clean or clean in skip_words:
                continue
            if len(clean) <= 1:
                continue
            normalized.append(token.strip())
        return normalized

    def _select_hook_keywords(self, core_keywords: list[str]) -> list[str]:
        preferred = ["爆款", "技巧", "教程", "避坑", "案例", "步骤", "秘诀", "真相"]
        hooks = [item for item in core_keywords if item in preferred]
        if len(hooks) < 3:
            hooks.extend(item for item in core_keywords if item not in hooks)
        return hooks[:5]

    def _build_visual_keywords(self, *, style: str, content_type: str) -> list[str]:
        base = ["强对比画面", "前3秒抓人", "字幕节奏清晰"]
        if style:
            base.append(f"{style}风格")
        if content_type:
            base.append(f"{content_type}表达")
        return base[:5]

    def _build_title_candidates(self, *, domain: str, hook_keywords: list[str]) -> list[str]:
        keyword = hook_keywords[0] if hook_keywords else domain
        return [
            f"{domain} 里最容易出爆款的 {keyword}",
            f"{domain} 短视频的 3 个高热开头",
            f"{domain} 内容怎么做更容易被看完",
        ]

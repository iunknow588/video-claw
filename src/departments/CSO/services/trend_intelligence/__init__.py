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
        script_topic_variants = self._build_script_topic_variants(
            domain=domain,
            title_candidates=title_candidates,
            audience=audience,
            publish_goal=publish_goal,
        )
        video_prompt_variants = self._build_video_prompt_variants(
            domain=domain,
            core_keywords=core_keywords,
            hook_keywords=hook_keywords,
            visual_keywords=visual_keywords,
            audience=audience,
            publish_goal=publish_goal,
        )
        image_prompt_variants = self._build_image_prompt_variants(
            domain=domain,
            core_keywords=core_keywords,
            visual_keywords=visual_keywords,
            style=style,
            content_type=content_type,
            audience=audience,
        )

        prompt_summary = (
            f"围绕“{domain}”领域，参考当前高热度短视频的结构、关键词和钩子句，"
            f"输出更适合 {content_type} 类型内容的短视频方案。"
        )
        script_topic = script_topic_variants[0] if script_topic_variants else domain
        video_prompt = video_prompt_variants[0] if video_prompt_variants else domain

        return {
            "core_keywords": core_keywords,
            "hook_keywords": hook_keywords,
            "visual_keywords": visual_keywords,
            "title_candidates": title_candidates,
            "prompt_summary": prompt_summary,
            "script_topic": script_topic,
            "script_topic_variants": script_topic_variants,
            "video_prompt": video_prompt,
            "video_prompt_variants": video_prompt_variants,
            "image_prompt_variants": image_prompt_variants,
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

    def _build_script_topic_variants(
        self,
        *,
        domain: str,
        title_candidates: list[str],
        audience: str | None,
        publish_goal: str | None,
    ) -> list[str]:
        variants = list(title_candidates)
        variants.extend(
            [
                f"{domain} 从 0 到 1 的高转化短视频拆解",
                f"{domain} 最容易被忽略的 3 个内容机会",
                f"{domain} 如何做出更容易看完的短视频结构",
            ]
        )
        if audience:
            variants.append(f"面向 {audience} 的 {domain} 短视频内容方案")
        if publish_goal:
            variants.append(f"围绕 {publish_goal} 目标的 {domain} 短视频脚本")
        return self._deduplicate_phrases(variants, limit=5)

    def _build_video_prompt_variants(
        self,
        *,
        domain: str,
        core_keywords: list[str],
        hook_keywords: list[str],
        visual_keywords: list[str],
        audience: str | None,
        publish_goal: str | None,
    ) -> list[str]:
        keyword_text = ", ".join(core_keywords[:6])
        hook_text = ", ".join(hook_keywords[:3])
        visual_text = ", ".join(visual_keywords[:4])
        audience_text = f"受众：{audience}；" if audience else ""
        goal_text = f"目标：{publish_goal}；" if publish_goal else ""
        variants = [
            f"主题：{domain}；{audience_text}{goal_text}核心关键词：{keyword_text}；开头钩子：{hook_text}；视觉风格：{visual_text}。",
            f"围绕 {domain} 制作 30 秒竖屏短视频，前 3 秒强钩子，突出 {hook_text}，画面强调 {visual_text}，内容围绕 {keyword_text} 展开。",
            f"生成 {domain} 的节奏型短视频，镜头快速切换、字幕清晰、重点突出，关键词包含 {keyword_text}，风格保持 {visual_text}。",
        ]
        return self._deduplicate_phrases(variants, limit=4)

    def _build_image_prompt_variants(
        self,
        *,
        domain: str,
        core_keywords: list[str],
        visual_keywords: list[str],
        style: str,
        content_type: str,
        audience: str | None,
    ) -> list[str]:
        keyword_text = ", ".join(core_keywords[:5])
        visual_text = ", ".join(visual_keywords[:4])
        audience_text = f"，目标受众为 {audience}" if audience else ""
        variants = [
            f"{domain} 短视频封面图，突出 {keyword_text}，{style} 风格，{content_type} 表达，强对比构图，适合移动端点击{audience_text}。",
            f"{domain} 关键视觉海报，包含 {keyword_text}，画面强调 {visual_text}，竖屏 9:16，适合作为视频首帧与封面。",
            f"{domain} 分镜预览图，展示人物或场景核心动作，保留 {visual_text}，适合后续图生视频参考。",
        ]
        return self._deduplicate_phrases(variants, limit=4)

    def _deduplicate_phrases(self, values: Iterable[str], *, limit: int) -> list[str]:
        deduplicated: list[str] = []
        seen: set[str] = set()
        for value in values:
            normalized = " ".join(str(value).split())
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            deduplicated.append(normalized)
            if len(deduplicated) >= limit:
                break
        return deduplicated

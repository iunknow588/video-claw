from __future__ import annotations


class DomainQueryExpansionSkill:
    skill_name = "lead.research.domain_query_expansion"
    CONTENT_TYPE_LABELS = {
        "knowledge": "知识讲解类",
        "news": "热点口播类",
        "review": "测评对比类",
        "story": "剧情演绎类",
        "product": "种草推荐类",
    }
    PLATFORM_LABELS = {
        "douyin": "抖音",
        "xiaohongshu": "小红书",
        "xigua": "西瓜视频",
        "bilibili": "B站",
    }

    def run(self, input_bundle: dict) -> dict:
        domain = str(input_bundle.get("domain", "") or "").strip()
        platform = str(input_bundle.get("platform", "") or "").strip()
        content_type = str(input_bundle.get("content_type", "") or "").strip()
        audience = str(input_bundle.get("audience", "") or "").strip()
        publish_goal = str(input_bundle.get("publish_goal", "") or "").strip()
        content_type_label = self.CONTENT_TYPE_LABELS.get(content_type, content_type)
        platform_label = self.PLATFORM_LABELS.get(platform, platform)

        candidates = [
            domain,
            f"{domain} {content_type_label}" if content_type_label else "",
            f"{platform_label} {domain}" if platform_label else "",
            f"{platform_label} {domain} {content_type_label}" if platform_label and content_type_label else "",
            f"{domain} 热点",
            f"{domain} 爆款",
            f"{domain} {audience}" if audience else "",
            f"{domain} {publish_goal}" if publish_goal else "",
        ]

        expanded_queries: list[str] = []
        seen: set[str] = set()
        for item in candidates:
            normalized = " ".join(str(item).split())
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            expanded_queries.append(normalized)

        return {"expanded_queries": expanded_queries[:6]}

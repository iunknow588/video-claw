from __future__ import annotations


class PromptValidationSkill:
    skill_name = "lead.research_development.prompt_validation"

    def run(self, input_bundle: dict) -> dict:
        prompt_bundle = dict(input_bundle)
        issues: list[str] = []
        warnings: list[str] = []

        required_text_fields = ("prompt_summary", "script_topic", "video_prompt")
        for field in required_text_fields:
            value = str(prompt_bundle.get(field) or "").strip()
            if not value:
                issues.append(f"{field} 不能为空。")

        list_rules = {
            "core_keywords": 3,
            "hook_keywords": 2,
            "title_candidates": 3,
            "script_topic_variants": 3,
            "video_prompt_variants": 2,
            "image_prompt_variants": 2,
        }
        for field, minimum in list_rules.items():
            values = self._normalize_list(prompt_bundle.get(field))
            prompt_bundle[field] = values
            if len(values) < minimum:
                issues.append(f"{field} 至少需要 {minimum} 项。")

        stop_words = {"the", "and", "for", "to", "or", "if", "of", "in", "on", "with"}
        noisy_keywords = [item for item in prompt_bundle.get("core_keywords", []) if item.lower() in stop_words]
        if noisy_keywords:
            warnings.append(f"core_keywords 含低价值停用词：{', '.join(noisy_keywords[:4])}。")

        blocked_noise = {"mock", "placeholder", "analysis", "mvp", "ai-video"}
        dirty_keywords = [item for item in prompt_bundle.get("core_keywords", []) if item.lower() in blocked_noise]
        if dirty_keywords:
            issues.append(f"core_keywords 含占位噪音词：{', '.join(dirty_keywords[:4])}。")

        first_video_prompt = str(prompt_bundle.get("video_prompt") or "")
        for marker in ("平台：", "时长：", "类型：", "视觉风格："):
            if marker not in first_video_prompt:
                warnings.append(f"video_prompt 缺少关键信息：{marker}")
        if any(marker in first_video_prompt.lower() for marker in blocked_noise):
            issues.append("video_prompt 含占位或调试噪音词。")

        quality_score = 1.0
        quality_score -= min(len(issues) * 0.2, 0.6)
        quality_score -= min(len(warnings) * 0.05, 0.2)
        quality_score = round(max(0.0, quality_score), 4)
        passed = not issues

        return {
            "passed": passed,
            "valid": passed,
            "issues": issues,
            "warnings": warnings,
            "quality_score": quality_score,
            "prompt_bundle": prompt_bundle,
        }

    @staticmethod
    def _normalize_list(value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        normalized: list[str] = []
        for item in value:
            text = str(item or "").strip()
            if text and text not in normalized:
                normalized.append(text)
        return normalized

from __future__ import annotations

from typing import Any

from departments.CEO.skills.base import BaseSkill


class TechnicalSpecCheckSkill(BaseSkill):
    skill_name = "lead.qa.technical_spec_check"
    description = "Checks duration, resolution, and platform-format constraints before publish."
    parameters_schema = {
        "type": "object",
        "properties": {
            "platform": {"type": "string"},
            "script": {"type": "object"},
            "video_task": {"type": ["object", "null"]},
        },
        "required": ["platform", "script"],
    }
    tags = ["lead", "qa", "technical"]
    retry_policy = {"max_retries": 1, "backoff": 0.0}
    dependencies = ["lead.production.video_task", "lead.publish.platform_adapter"]
    required_tokens = ["platform", "script", "video_task"]

    PLATFORM_LIMITS = {
        "douyin": {"min_duration": 5, "max_duration": 180, "sizes": {"1080x1920", "720x1280"}},
        "xiaohongshu": {"min_duration": 5, "max_duration": 180, "sizes": {"1080x1920", "720x1280"}},
        "xigua": {"min_duration": 10, "max_duration": 600, "sizes": {"1920x1080", "1080x1920"}},
        "bilibili": {"min_duration": 10, "max_duration": 600, "sizes": {"1920x1080", "1080x1920"}},
    }

    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        platform = str(input_data.get("platform") or "douyin")
        script = input_data.get("script") or {}
        task = input_data.get("video_task") or {}
        limits = self.PLATFORM_LIMITS.get(platform, self.PLATFORM_LIMITS["douyin"])

        issues: list[str] = []
        score = 1.0
        duration = int(script.get("duration") or 0)
        if duration < limits["min_duration"] or duration > limits["max_duration"]:
            issues.append(
                f"时长 {duration}s 不符合 {platform} 平台要求（{limits['min_duration']}-{limits['max_duration']}s）。"
            )
            score -= 0.45

        if task:
            size = task.get("size")
            if size not in limits["sizes"]:
                issues.append(f"分辨率 {size} 与 {platform} 平台建议规格不匹配。")
                score -= 0.2

        passed = score >= 0.75
        if passed and not issues:
            issues.append("时长、分辨率和平台发布规格均在可接受范围内。")

        return {
            "dimension": "technical_spec",
            "applicable": True,
            "pass": passed,
            "score": round(max(score, 0.0), 4),
            "issues": issues,
            "recommendation": "通过，可进入最终发布。" if passed else "建议回到生产组调整时长或导出规格。",
        }

    def validate_input(self, input_data: dict[str, Any]) -> bool:
        return isinstance(input_data, dict) and "platform" in input_data and "script" in input_data


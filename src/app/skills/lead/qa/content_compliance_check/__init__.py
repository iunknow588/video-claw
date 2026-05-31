from __future__ import annotations

from typing import Any

from app.skills.base import BaseSkill


class ContentComplianceCheckSkill(BaseSkill):
    skill_name = "lead.qa.content_compliance_check"
    description = "Checks script and video payloads for sensitive content and platform safety issues."
    parameters_schema = {
        "type": "object",
        "properties": {
            "script": {"type": "object"},
            "video_task": {"type": ["object", "null"]},
            "platform": {"type": "string"},
        },
        "required": ["script", "platform"],
    }
    tags = ["lead", "qa", "compliance"]
    retry_policy = {"max_retries": 1, "backoff": 0.0}
    dependencies = ["lead.analysis.risk_extraction", "lead.production.script_review"]
    required_tokens = ["script"]

    BLOCKED_TERMS = ("赌博", "暴利", "保赚", "违禁", "绝密外挂")
    WARNING_TERMS = ("最强", "绝对", "100%", "稳赚")

    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        script = input_data.get("script") or {}
        task = input_data.get("video_task") or {}
        text_fields = [
            str(script.get("title") or ""),
            str(script.get("hook") or ""),
            str(script.get("cta") or ""),
        ]
        flattened = "\n".join(text_fields)

        issues: list[str] = []
        blocked = [term for term in self.BLOCKED_TERMS if term in flattened]
        warned = [term for term in self.WARNING_TERMS if term in flattened]
        score = 1.0

        if blocked:
            issues.append(f"发现敏感表达：{', '.join(blocked)}。")
            score -= 0.6
        if warned:
            issues.append(f"存在高风险营销措辞：{', '.join(warned)}。")
            score -= 0.15
        if task and "watermark" in str(task.get("video_url") or "").lower():
            issues.append("检测到疑似平台水印残留。")
            score -= 0.2

        passed = score >= 0.75
        if passed and not issues:
            issues.append("未发现明显违规词或平台敏感元素。")

        return {
            "dimension": "content_compliance",
            "applicable": True,
            "pass": passed,
            "score": round(max(score, 0.0), 4),
            "issues": issues,
            "recommendation": "通过，可进入爆款基因与技术参数复核。" if passed else "建议回退到策划或生产组修正文案与素材。",
        }

    def validate_input(self, input_data: dict[str, Any]) -> bool:
        return isinstance(input_data, dict) and "script" in input_data and "platform" in input_data


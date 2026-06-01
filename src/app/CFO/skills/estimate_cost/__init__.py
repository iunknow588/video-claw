from __future__ import annotations

from typing import Any

from app.CEO.skills.base import BaseSkill


class EstimateCostSkill(BaseSkill):
    skill_name = "lead.cfo.estimate_cost"
    description = "Estimates token demand, provider mix, and expected spend before production starts."
    parameters_schema = {
        "type": "object",
        "properties": {
            "domain": {"type": "string"},
            "platform": {"type": "string"},
            "duration": {"type": "integer"},
            "hotspot_count": {"type": "integer"},
            "top_n": {"type": "integer"},
            "auto_generate_video": {"type": "boolean"},
        },
        "required": ["domain", "platform"],
    }
    tags = ["lead", "cfo", "finance", "gate"]
    dependencies = ["ceo.workflow"]
    required_tokens = ["domain", "platform"]

    PLATFORM_FACTORS = {
        "douyin": 1.0,
        "xiaohongshu": 1.05,
        "bilibili": 1.1,
    }

    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        duration = int(input_data.get("duration") or 30)
        hotspot_count = int(input_data.get("hotspot_count") or 12)
        top_n = int(input_data.get("top_n") or 3)
        auto_generate_video = bool(input_data.get("auto_generate_video"))
        platform = str(input_data.get("platform") or "douyin").lower()
        platform_factor = self.PLATFORM_FACTORS.get(platform, 1.0)

        token_breakdown = {
            "lead.cfo": 220,
            "lead.research": 480 + hotspot_count * 110,
            "lead.analysis": 420 + top_n * 650,
            "lead.research_development": 650 + top_n * 220,
            "lead.production": 780 + duration * 14 + (1200 if auto_generate_video else 240),
            "lead.qa": 360 + (260 if auto_generate_video else 120),
            "lead.publish": 240 + (120 if auto_generate_video else 60),
        }
        adjusted_breakdown = {
            stage: int(round(tokens * platform_factor))
            for stage, tokens in token_breakdown.items()
        }
        estimated_tokens = sum(adjusted_breakdown.values())
        estimated_cost = round((estimated_tokens / 1000) * 0.018 + (0.12 if auto_generate_video else 0.0), 4)
        required_services = ["deepseek", "glm"]
        if auto_generate_video:
            required_services.append("seedance")

        return {
            "finance_estimate": {
                "estimated_tokens": estimated_tokens,
                "estimated_cost": estimated_cost,
                "currency": "USD",
                "estimated_tokens_by_leader": adjusted_breakdown,
                "required_services": required_services,
                "platform_factor": platform_factor,
                "assumptions": [
                    "research and analysis scale with hotspot_count/top_n",
                    "video generation reserves extra seedance quota",
                    "cost model is a lightweight preflight estimate rather than provider billing",
                ],
            }
        }

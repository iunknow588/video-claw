from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.skills.base import BaseSkill


class VerifyBalanceSkill(BaseSkill):
    skill_name = "lead.cfo.verify_balance"
    description = "Checks provider readiness and remaining budget before CFO releases the task."
    parameters_schema = {
        "type": "object",
        "properties": {
            "estimated_cost": {"type": "number"},
            "required_services": {"type": "array"},
            "remaining_budget": {"type": "number"},
            "daily_budget": {"type": "number"},
            "actual_spend": {"type": "number"},
        },
        "required": ["estimated_cost", "required_services"],
    }
    tags = ["lead", "cfo", "finance", "gate"]
    dependencies = ["lead.cfo.estimate_cost"]
    required_tokens = ["required_services"]

    PROVIDER_KEYS = {
        "deepseek": "DEEPSEEK_API_KEY",
        "glm": "GLM_API_KEY",
        "seedance": "SEEDANCE_API_KEY",
    }

    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        estimated_cost = round(float(input_data.get("estimated_cost") or 0.0), 4)
        required_services = [str(item) for item in list(input_data.get("required_services") or [])]
        daily_budget = round(float(input_data.get("daily_budget") or settings.DAILY_BUDGET or 0.0), 4)
        actual_spend = round(float(input_data.get("actual_spend") or 0.0), 4)
        remaining_budget = round(
            float(input_data.get("remaining_budget") or max(daily_budget - actual_spend, 0.0)),
            4,
        )

        provider_status: dict[str, dict[str, Any]] = {}
        blocked_reasons: list[str] = []
        for provider in required_services:
            setting_name = self.PROVIDER_KEYS.get(provider)
            key_value = getattr(settings, setting_name, "") if setting_name else ""
            live_ready = bool(key_value)
            placeholder_ready = bool(settings.AI_USE_PLACEHOLDER_WHEN_UNCONFIGURED and not live_ready)
            ready = live_ready or placeholder_ready
            mode = "live" if live_ready else "placeholder" if placeholder_ready else "missing"
            provider_status[provider] = {
                "ready": ready,
                "mode": mode,
                "configured": live_ready,
            }
            if not ready:
                blocked_reasons.append(f"{provider} provider is unavailable")

        if remaining_budget < estimated_cost:
            blocked_reasons.append(
                f"remaining budget {remaining_budget:.4f} is lower than required {estimated_cost:.4f}"
            )

        passed = not blocked_reasons
        return {
            "finance_check": {
                "passed": passed,
                "estimated_cost": estimated_cost,
                "daily_budget": daily_budget,
                "actual_spend": actual_spend,
                "remaining_budget": remaining_budget,
                "provider_status": provider_status,
                "blocked_reasons": blocked_reasons,
                "message": "finance gate passed" if passed else "finance gate blocked",
            }
        }

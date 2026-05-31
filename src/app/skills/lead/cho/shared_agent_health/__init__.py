from __future__ import annotations

from typing import Any

from app.skills.base import BaseSkill
from app.skills.lead.cho.public_agent_registry import PUBLIC_AGENT_ROSTER


class SharedAgentHealthSkill(BaseSkill):
    skill_name = "lead.cho.shared_agent_health"
    description = "Summarizes availability and governance health for CHO-managed public agents."
    parameters_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["check_health"],
            },
        },
        "required": ["action"],
    }
    tags = ["lead", "cho", "agent", "health"]
    dependencies = ["lead.cho.public_agent_registry", "lead.cio.log"]

    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        action = str(input_data.get("action") or "")
        if action != "check_health":
            raise ValueError(f"Unsupported action for {self.skill_name}: {action}")

        health_items = []
        for item in PUBLIC_AGENT_ROSTER:
            health_items.append(
                {
                    "agent_name": item["agent_name"],
                    "owner_leader": item["owner_leader"],
                    "availability": "ready",
                    "governance_status": "managed",
                    "integration_scope": item["scope"],
                }
            )
        return {
            "health_items": health_items,
            "ready_count": len(health_items),
            "warning_count": 0,
        }

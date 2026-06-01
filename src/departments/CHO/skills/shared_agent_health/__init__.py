from __future__ import annotations

from typing import Any

from departments.CEO.skills.base import BaseSkill
from departments.CHO.services.service import CHOService


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
        return CHOService().check_health()

from __future__ import annotations

from typing import Any

from app.CEO.skills.base import BaseSkill
from app.CHO.services.service import CHOService


class AgentCapabilitySkill(BaseSkill):
    skill_name = "lead.cho.agent_capability"
    description = "Explains what a CHO-managed public agent is responsible for and how it is integrated."
    parameters_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["describe_agent", "list_capabilities"],
            },
            "agent_name": {"type": "string"},
        },
        "required": ["action"],
    }
    tags = ["lead", "cho", "agent", "capability"]
    dependencies = ["lead.cho.public_agent_registry"]

    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        action = str(input_data.get("action") or "")
        service = CHOService()
        if action == "list_capabilities":
            return service.list_capabilities()
        if action == "describe_agent":
            return service.describe_agent(str(input_data.get("agent_name") or "").strip())
        raise ValueError(f"Unsupported action for {self.skill_name}: {action}")

from __future__ import annotations

from typing import Any

from app.CEO.skills.base import BaseSkill
from app.CHO.services.service import CHOService


class PublicAgentRegistrySkill(BaseSkill):
    skill_name = "lead.cho.public_agent_registry"
    description = "Maintains the CHO-managed roster of shared and public agent entrypoints."
    parameters_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["list_public_agents", "get_public_agent"],
            },
            "agent_name": {"type": "string"},
        },
        "required": ["action"],
    }
    tags = ["lead", "cho", "agent", "registry"]
    dependencies = ["lead.cio.query_log"]

    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        action = str(input_data.get("action") or "")
        service = CHOService()
        if action == "list_public_agents":
            return service.list_public_agents()
        if action == "get_public_agent":
            return service.get_public_agent(str(input_data.get("agent_name") or "").strip())
        raise ValueError(f"Unsupported action for {self.skill_name}: {action}")

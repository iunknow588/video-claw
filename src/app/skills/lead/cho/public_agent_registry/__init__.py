from __future__ import annotations

from typing import Any

from app.skills.base import BaseSkill


PUBLIC_AGENT_ROSTER: list[dict[str, Any]] = [
    {
        "agent_name": "CMOAgent",
        "entrypoint": "app.CMO.agent.CMOAgent",
        "domain": "promotion_interface",
        "scope": "user_facing",
        "owner_leader": "lead.promotion",
    },
    {
        "agent_name": "CFOAgent",
        "entrypoint": "app.CFO.agent.CFOAgent",
        "domain": "finance_gate",
        "scope": "shared_support",
        "owner_leader": "lead.cfo",
    },
    {
        "agent_name": "CIOAgent",
        "entrypoint": "app.CIO.agent.CIOAgent",
        "domain": "information_hub",
        "scope": "shared_support",
        "owner_leader": "lead.cio",
    },
    {
        "agent_name": "ResearchAgent",
        "entrypoint": "app.Research.agent.ResearchAgent",
        "domain": "research",
        "scope": "production_support",
        "owner_leader": "lead.research",
    },
    {
        "agent_name": "AnalysisAgent",
        "entrypoint": "app.Analysis.agent.AnalysisAgent",
        "domain": "analysis",
        "scope": "production_support",
        "owner_leader": "lead.analysis",
    },
    {
        "agent_name": "ProductionAgent",
        "entrypoint": "app.Production.agent.ProductionAgent",
        "domain": "production",
        "scope": "production_core",
        "owner_leader": "lead.production",
    },
    {
        "agent_name": "CAOAgent",
        "entrypoint": "app.CAO.agent.CAOAgent",
        "domain": "external_api_gateway",
        "scope": "external_interface",
        "owner_leader": "lead.publish",
    },
]


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
        if action == "list_public_agents":
            return {
                "public_agents": list(PUBLIC_AGENT_ROSTER),
                "count": len(PUBLIC_AGENT_ROSTER),
            }
        if action == "get_public_agent":
            agent_name = str(input_data.get("agent_name") or "").strip().lower()
            selected = next(
                (item for item in PUBLIC_AGENT_ROSTER if str(item.get("agent_name") or "").lower() == agent_name),
                None,
            )
            return {"public_agent": selected, "found": selected is not None}
        raise ValueError(f"Unsupported action for {self.skill_name}: {action}")

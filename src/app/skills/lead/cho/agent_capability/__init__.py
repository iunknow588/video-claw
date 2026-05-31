from __future__ import annotations

from typing import Any

from app.skills.base import BaseSkill
from app.skills.lead.cho.public_agent_registry import PUBLIC_AGENT_ROSTER


AGENT_CAPABILITY_MAP: dict[str, dict[str, Any]] = {
    "CMOAgent": {
        "capabilities": ["user_message_intake", "progress_broadcast", "report_formatting"],
        "integration_type": "user_channel",
    },
    "CFOAgent": {
        "capabilities": ["cost_estimation", "budget_gate", "charge_receipt"],
        "integration_type": "finance_gate",
    },
    "CIOAgent": {
        "capabilities": ["artifact_storage", "log_query", "knowledge_base"],
        "integration_type": "information_hub",
    },
    "ResearchAgent": {
        "capabilities": ["trend_discovery", "query_expansion", "material_search"],
        "integration_type": "production_support",
    },
    "AnalysisAgent": {
        "capabilities": ["structure_analysis", "hook_extraction", "risk_detection"],
        "integration_type": "production_support",
    },
    "ProductionAgent": {
        "capabilities": ["script_drafting", "subtitle_compose", "render_execution"],
        "integration_type": "production_core",
    },
    "CAOAgent": {
        "capabilities": ["platform_adaptation", "publish_execution", "callback_tracking"],
        "integration_type": "external_api_gateway",
    },
}


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
        if action == "list_capabilities":
            return {"capabilities_by_agent": dict(AGENT_CAPABILITY_MAP)}
        if action == "describe_agent":
            agent_name = str(input_data.get("agent_name") or "").strip()
            roster_item = next((item for item in PUBLIC_AGENT_ROSTER if item["agent_name"] == agent_name), None)
            capability_item = AGENT_CAPABILITY_MAP.get(agent_name)
            return {
                "agent_name": agent_name,
                "registry_entry": roster_item,
                "capability_profile": capability_item,
                "found": roster_item is not None and capability_item is not None,
            }
        raise ValueError(f"Unsupported action for {self.skill_name}: {action}")

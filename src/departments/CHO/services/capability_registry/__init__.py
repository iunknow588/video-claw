from __future__ import annotations

from copy import deepcopy
from typing import Any

from departments.CHO.services.agent_management import AgentLifecycleService


DEFAULT_AGENT_CAPABILITY_MAP: dict[str, dict[str, Any]] = {
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


def build_default_capability_store() -> dict[str, dict[str, Any]]:
    return {name: deepcopy(profile) for name, profile in DEFAULT_AGENT_CAPABILITY_MAP.items()}


class CapabilityRegistryService:
    """Own the CHO capability directory for shared and public agents."""

    def __init__(
        self,
        lifecycle_service: AgentLifecycleService,
        capability_store: dict[str, dict[str, Any]] | None = None,
    ):
        self.lifecycle_service = lifecycle_service
        self._capability_store = capability_store if capability_store is not None else build_default_capability_store()

    def list_capabilities(self) -> dict[str, dict[str, Any]]:
        catalog: dict[str, dict[str, Any]] = {}
        for item in self.lifecycle_service.list_public_agents():
            agent_name = str(item["agent_name"])
            profile = self._capability_store.get(agent_name, {})
            catalog[agent_name] = {
                "capabilities": list(profile.get("capabilities") or []),
                "integration_type": profile.get("integration_type"),
                "owner_leader": item.get("owner_leader"),
                "lifecycle_status": item.get("lifecycle_status"),
            }
        return catalog

    def describe_agent(self, agent_name: str) -> dict[str, Any]:
        registry_entry = self.lifecycle_service.get_public_agent(agent_name)
        capability_profile = self._capability_store.get(str(agent_name).strip())
        return {
            "agent_name": str(agent_name).strip(),
            "registry_entry": deepcopy(registry_entry),
            "capability_profile": deepcopy(capability_profile),
            "found": registry_entry is not None and capability_profile is not None,
        }

    def update_capabilities(
        self,
        agent_name: str,
        capabilities: list[str],
        *,
        integration_type: str | None = None,
    ) -> dict[str, Any]:
        registry_entry = self.lifecycle_service.get_public_agent(agent_name)
        if registry_entry is None:
            raise ValueError(f"Unknown public agent: {agent_name}")

        normalized_name = str(agent_name).strip()
        profile = self._capability_store.setdefault(normalized_name, {})
        profile["capabilities"] = [str(item).strip() for item in capabilities if str(item).strip()]
        profile["integration_type"] = (
            integration_type
            if integration_type is not None
            else profile.get("integration_type") or registry_entry.get("domain")
        )
        return deepcopy(profile)

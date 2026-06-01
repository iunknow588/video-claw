from __future__ import annotations

from copy import deepcopy
from typing import Any


DEFAULT_PUBLIC_AGENT_ROSTER: list[dict[str, Any]] = [
    {
        "agent_name": "CMOAgent",
        "entrypoint": "app.CMO.agent.CMOAgent",
        "domain": "promotion_interface",
        "scope": "user_facing",
        "owner_leader": "lead.promotion",
        "lifecycle_status": "active",
    },
    {
        "agent_name": "CFOAgent",
        "entrypoint": "app.CFO.agent.CFOAgent",
        "domain": "finance_gate",
        "scope": "shared_support",
        "owner_leader": "lead.cfo",
        "lifecycle_status": "active",
    },
    {
        "agent_name": "CIOAgent",
        "entrypoint": "app.CIO.agent.CIOAgent",
        "domain": "information_hub",
        "scope": "shared_support",
        "owner_leader": "lead.cio",
        "lifecycle_status": "active",
    },
    {
        "agent_name": "ResearchAgent",
        "entrypoint": "app.CSO.agent.ResearchAgent",
        "domain": "CSO",
        "scope": "production_support",
        "owner_leader": "lead.research",
        "lifecycle_status": "active",
    },
    {
        "agent_name": "AnalysisAgent",
        "entrypoint": "app.CCO.agent.AnalysisAgent",
        "domain": "CCO",
        "scope": "production_support",
        "owner_leader": "lead.analysis",
        "lifecycle_status": "active",
    },
    {
        "agent_name": "ProductionAgent",
        "entrypoint": "app.COO.agent.ProductionAgent",
        "domain": "COO",
        "scope": "production_core",
        "owner_leader": "lead.production",
        "lifecycle_status": "active",
    },
    {
        "agent_name": "CAOAgent",
        "entrypoint": "app.CAO.agent.CAOAgent",
        "domain": "external_api_gateway",
        "scope": "external_interface",
        "owner_leader": "lead.publish",
        "lifecycle_status": "active",
    },
]


def build_default_agent_store() -> dict[str, dict[str, Any]]:
    return {item["agent_name"]: deepcopy(item) for item in DEFAULT_PUBLIC_AGENT_ROSTER}


class AgentLifecycleService:
    """Manage the lifecycle and registry identity of CHO-governed public agents."""

    def __init__(self, agent_store: dict[str, dict[str, Any]] | None = None):
        self._agent_store = agent_store if agent_store is not None else build_default_agent_store()

    def list_public_agents(self, *, include_inactive: bool = False) -> list[dict[str, Any]]:
        agents = []
        for item in sorted(self._agent_store.values(), key=lambda record: str(record["agent_name"])):
            if not include_inactive and item.get("lifecycle_status") != "active":
                continue
            agents.append(deepcopy(item))
        return agents

    def get_public_agent(
        self,
        agent_name: str,
        *,
        include_inactive: bool = True,
    ) -> dict[str, Any] | None:
        normalized_name = self._normalize_agent_name(agent_name)
        record = self._agent_store.get(normalized_name)
        if record is None:
            return None
        if not include_inactive and record.get("lifecycle_status") != "active":
            return None
        return deepcopy(record)

    def provision_agent(self, spec: dict[str, Any]) -> dict[str, Any]:
        agent_name = self._normalize_agent_name(spec.get("agent_name"))
        if not agent_name:
            raise ValueError("agent_name is required")

        record = {
            "agent_name": agent_name,
            "entrypoint": self._require_string(spec, "entrypoint"),
            "domain": self._require_string(spec, "domain"),
            "scope": self._require_string(spec, "scope"),
            "owner_leader": self._require_string(spec, "owner_leader"),
            "lifecycle_status": str(spec.get("lifecycle_status") or "active"),
        }
        self._agent_store[agent_name] = record
        return deepcopy(record)

    def decommission_agent(self, agent_name: str) -> None:
        normalized_name = self._normalize_agent_name(agent_name)
        record = self._agent_store.get(normalized_name)
        if record is None:
            raise ValueError(f"Unknown public agent: {agent_name}")
        record["lifecycle_status"] = "decommissioned"

    def update_agent(self, agent_name: str, updates: dict[str, Any]) -> dict[str, Any]:
        normalized_name = self._normalize_agent_name(agent_name)
        record = self._agent_store.get(normalized_name)
        if record is None:
            raise ValueError(f"Unknown public agent: {agent_name}")

        for field in ("entrypoint", "domain", "scope", "owner_leader", "lifecycle_status"):
            if field in updates and updates[field] is not None:
                record[field] = str(updates[field])
        return deepcopy(record)

    def _normalize_agent_name(self, raw_name: Any) -> str:
        return str(raw_name or "").strip()

    def _require_string(self, spec: dict[str, Any], key: str) -> str:
        value = str(spec.get(key) or "").strip()
        if not value:
            raise ValueError(f"{key} is required")
        return value

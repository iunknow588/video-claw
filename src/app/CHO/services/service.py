from __future__ import annotations

from typing import Any

from app.CHO.services.agent_management import AgentLifecycleService, build_default_agent_store
from app.CHO.services.capability_registry import CapabilityRegistryService, build_default_capability_store
from app.CHO.services.health_monitoring import HealthMonitoringService


class CHOService:
    """Department-level CHO facade for public-agent governance use cases."""

    def __init__(self):
        lifecycle_service = AgentLifecycleService(build_default_agent_store())
        capability_registry = CapabilityRegistryService(
            lifecycle_service=lifecycle_service,
            capability_store=build_default_capability_store(),
        )
        self.agent_management = lifecycle_service
        self.capability_registry = capability_registry
        self.health_monitoring = HealthMonitoringService(lifecycle_service, capability_registry)

    def list_public_agents(self) -> dict[str, Any]:
        agents = self.agent_management.list_public_agents()
        return {"public_agents": agents, "count": len(agents)}

    def get_public_agent(self, agent_name: str) -> dict[str, Any]:
        selected = self.agent_management.get_public_agent(agent_name)
        return {"public_agent": selected, "found": selected is not None}

    def provision_agent(self, spec: dict[str, Any]) -> dict[str, Any]:
        record = self.agent_management.provision_agent(spec)
        capabilities = [str(item).strip() for item in list(spec.get("capabilities") or []) if str(item).strip()]
        self.capability_registry.update_capabilities(
            record["agent_name"],
            capabilities,
            integration_type=spec.get("integration_type"),
        )
        return record

    def decommission_agent(self, agent_name: str) -> None:
        self.agent_management.decommission_agent(agent_name)

    def update_capabilities(self, agent_name: str, capabilities: list[str]) -> dict[str, Any]:
        return self.capability_registry.update_capabilities(agent_name, capabilities)

    def list_capabilities(self) -> dict[str, Any]:
        catalog = self.capability_registry.list_capabilities()
        return {"capabilities_by_agent": catalog, "count": len(catalog)}

    def describe_agent(self, agent_name: str) -> dict[str, Any]:
        return self.capability_registry.describe_agent(agent_name)

    def check_health(self) -> dict[str, Any]:
        return self.health_monitoring.check_health()

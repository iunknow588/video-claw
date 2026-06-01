from __future__ import annotations

from typing import Any

from app.CHO.services.agent_management import AgentLifecycleService
from app.CHO.services.capability_registry import CapabilityRegistryService


class HealthMonitoringService:
    """Summarize availability and governance health for CHO-managed agents."""

    def __init__(
        self,
        lifecycle_service: AgentLifecycleService,
        capability_registry: CapabilityRegistryService,
    ):
        self.lifecycle_service = lifecycle_service
        self.capability_registry = capability_registry

    def check_health(self) -> dict[str, Any]:
        health_items: list[dict[str, Any]] = []
        warning_count = 0

        for item in self.lifecycle_service.list_public_agents(include_inactive=True):
            agent_name = str(item["agent_name"])
            capability_profile = self.capability_registry.describe_agent(agent_name)["capability_profile"] or {}
            lifecycle_status = str(item.get("lifecycle_status") or "unknown")
            capabilities = list(capability_profile.get("capabilities") or [])

            availability = "ready" if lifecycle_status == "active" else "offline"
            governance_status = "managed" if capabilities else "needs_capability_profile"
            if lifecycle_status != "active" or governance_status != "managed":
                warning_count += 1

            health_items.append(
                {
                    "agent_name": agent_name,
                    "owner_leader": item["owner_leader"],
                    "availability": availability,
                    "governance_status": governance_status,
                    "integration_scope": item["scope"],
                    "lifecycle_status": lifecycle_status,
                }
            )

        ready_count = sum(1 for item in health_items if item["availability"] == "ready")
        return {
            "health_items": health_items,
            "ready_count": ready_count,
            "warning_count": warning_count,
        }

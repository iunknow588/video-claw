from __future__ import annotations

from app.CEO.config.agent import CEOConfigAgent
from app.CIO.services.config_platform import ConfigManager, get_config_manager


class ConfigGovernancePolicy:
    """CEO-owned policy layer for config ownership and mutation checks."""

    def __init__(self, manager: ConfigManager | None = None) -> None:
        self.manager = manager or get_config_manager()
        self.agent = CEOConfigAgent(self.manager)

    def can_modify(self, domain: str, key: str, operator: str) -> bool:
        permissions = self.agent.load_permissions()
        allowed = permissions.domain_permissions.get(domain, [])
        return operator in allowed or operator == "CEO"

    def is_dynamic(self, key: str) -> bool:
        permissions = self.agent.load_permissions()
        return key in set(permissions.dynamic_keys)

    def owner_of(self, domain: str) -> str | None:
        departments = self.agent.load_departments()
        return departments.owners.get(domain)

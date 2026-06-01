from __future__ import annotations

from app.CIO.services.config_platform import ConfigManager


class CEOConfigAgent:
    """CEO-owned access agent for governance configuration domains."""

    def __init__(self, manager: ConfigManager) -> None:
        self.manager = manager

    def load_application(self):
        return self.manager.load_config(
            domain="ceo_application",
            model_class="app.CEO.config.schema.ApplicationGovernanceConfig",
        )

    def load_permissions(self):
        return self.manager.load_config(
            domain="ceo_permissions",
            model_class="app.CEO.config.schema.PermissionMatrixConfig",
        )

    def load_leaders(self):
        return self.manager.load_config(
            domain="ceo_leaders",
            model_class="app.CEO.config.schema.ControlPlaneLeadersConfig",
        )

    def load_departments(self):
        return self.manager.load_config(
            domain="ceo_departments",
            model_class="app.CEO.config.schema.DepartmentsGovernanceConfig",
        )

    def load_workflow(self):
        return self.manager.load_config(
            domain="ceo_workflow",
            model_class="app.CEO.config.schema.WorkflowGovernanceConfig",
        )

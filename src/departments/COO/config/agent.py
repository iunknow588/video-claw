from __future__ import annotations

from departments.CIO.services.config_platform import ConfigManager


class COOConfigAgent:
    """COO-owned access agent for production configuration."""

    def __init__(self, manager: ConfigManager) -> None:
        self.manager = manager

    def load_production(self):
        return self.manager.load_config(
            domain="coo_production",
            model_class="departments.COO.config.schema.ProductionConfig",
        )

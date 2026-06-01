from __future__ import annotations

from app.CIO.services.config_platform import ConfigManager


class COOConfigAgent:
    """COO-owned access agent for production configuration."""

    def __init__(self, manager: ConfigManager) -> None:
        self.manager = manager

    def load_production(self):
        return self.manager.load_config(
            domain="coo_production",
            model_class="app.COO.config.schema.ProductionConfig",
        )

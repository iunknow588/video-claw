from __future__ import annotations

from app.CIO.services.config_platform import ConfigManager


class CFOConfigAgent:
    """CFO-owned access agent for finance configuration."""

    def __init__(self, manager: ConfigManager) -> None:
        self.manager = manager

    def load_finance(self):
        return self.manager.load_config(
            domain="cfo_finance",
            model_class="app.CFO.config.schema.FinanceConfig",
        )

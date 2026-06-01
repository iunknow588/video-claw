from __future__ import annotations

from departments.CIO.services.config_platform import ConfigManager


class CSOConfigAgent:
    """CSO-owned access agent for hotspot collection configuration."""

    def __init__(self, manager: ConfigManager) -> None:
        self.manager = manager

    def load_hotspot(self):
        return self.manager.load_config(
            domain="cso_hotspot",
            model_class="departments.CSO.config.schema.HotspotConfig",
        )

from __future__ import annotations

from app.CIO.services.config_platform.manager import ConfigManager


_config_manager = ConfigManager()


def get_config_manager() -> ConfigManager:
    return _config_manager

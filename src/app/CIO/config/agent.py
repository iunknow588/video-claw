from __future__ import annotations

from app.CIO.services.config_platform import ConfigManager


class CIOInfrastructureConfigAgent:
    """CIO-owned access agent for infrastructure configuration domains."""

    def __init__(self, manager: ConfigManager) -> None:
        self.manager = manager

    def load_database(self):
        return self.manager.load_config(
            domain="cio_database",
            model_class="app.CIO.config.schema.DatabaseConfig",
        )

    def load_redis(self):
        return self.manager.load_config(
            domain="cio_redis",
            model_class="app.CIO.config.schema.RedisConfig",
        )

    def load_ai_providers(self):
        return self.manager.load_config(
            domain="cio_ai_providers",
            model_class="app.CIO.config.schema.AIProvidersConfig",
        )

    def load_storage(self):
        return self.manager.load_config(
            domain="cio_storage",
            model_class="app.CIO.config.schema.StorageConfig",
        )

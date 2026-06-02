"""
Centralized application configuration runtime.
"""

from __future__ import annotations

import os
from typing import Any
from pathlib import Path

from dotenv import load_dotenv

from departments.CEO.config.agent import CEOConfigAgent
from departments.CFO.config.agent import CFOConfigAgent
from departments.CIO.config.agent import CIOInfrastructureConfigAgent
from departments.CIO.services.config_platform import ConfigManager, get_config_manager
from departments.COO.config.agent import COOConfigAgent
from departments.CSO.config.agent import CSOConfigAgent


ROOT_ENV_PATH = Path(__file__).resolve().parents[5] / ".env"
load_dotenv(ROOT_ENV_PATH, override=False)


def _apply_provider_env_aliases() -> None:
    """Normalize provider env aliases from vendor samples into app runtime keys."""

    if not os.environ.get("SEEDANCE_API_KEY") and os.environ.get("ARK_API_KEY"):
        os.environ["SEEDANCE_API_KEY"] = os.environ["ARK_API_KEY"]
    if not os.environ.get("SEEDANCE_BASE_URL") and os.environ.get("ARK_BASE_URL"):
        os.environ["SEEDANCE_BASE_URL"] = os.environ["ARK_BASE_URL"]
    if not os.environ.get("SEEDANCE_MODEL"):
        ark_video_model = os.environ.get("ARK_VIDEO_MODEL") or os.environ.get("ARK_MODEL")
        if ark_video_model:
            os.environ["SEEDANCE_MODEL"] = ark_video_model
    if not os.environ.get("SEEDANCE_RESOURCE_ID") and os.environ.get("ARK_RESOURCE_ID"):
        os.environ["SEEDANCE_RESOURCE_ID"] = os.environ["ARK_RESOURCE_ID"]


DOMAIN_SPECS: dict[str, tuple[str, str]] = {
    "ceo_application": ("application", "departments.CEO.config.schema.ApplicationGovernanceConfig"),
    "ceo_leaders": ("leaders", "departments.CEO.config.schema.ControlPlaneLeadersConfig"),
    "ceo_permissions": ("permissions", "departments.CEO.config.schema.PermissionMatrixConfig"),
    "ceo_departments": ("departments", "departments.CEO.config.schema.DepartmentsGovernanceConfig"),
    "ceo_workflow": ("workflow", "departments.CEO.config.schema.WorkflowGovernanceConfig"),
    "cio_database": ("database", "departments.CIO.config.schema.DatabaseConfig"),
    "cio_redis": ("redis", "departments.CIO.config.schema.RedisConfig"),
    "cio_ai_providers": ("ai_providers", "departments.CIO.config.schema.AIProvidersConfig"),
    "cio_storage": ("storage", "departments.CIO.config.schema.StorageConfig"),
    "cfo_finance": ("finance", "departments.CFO.config.schema.FinanceConfig"),
    "coo_production": ("production", "departments.COO.config.schema.ProductionConfig"),
    "cso_hotspot": ("hotspot", "departments.CSO.config.schema.HotspotConfig"),
}


class Settings:
    """Single runtime-backed settings surface for the whole application."""

    def __init__(self, manager: ConfigManager | None = None) -> None:
        _apply_provider_env_aliases()
        self._manager = manager or get_config_manager()
        self._ceo_agent = CEOConfigAgent(self._manager)
        self._cio_agent = CIOInfrastructureConfigAgent(self._manager)
        self._cfo_agent = CFOConfigAgent(self._manager)
        self._coo_agent = COOConfigAgent(self._manager)
        self._cso_agent = CSOConfigAgent(self._manager)
        self.reload()

    def reload(self) -> "Settings":
        _apply_provider_env_aliases()
        self.application = self._ceo_agent.load_application()
        self.leaders = self._ceo_agent.load_leaders()
        self.permissions = self._ceo_agent.load_permissions()
        self.departments = self._ceo_agent.load_departments()
        self.workflow = self._ceo_agent.load_workflow()
        self.database = self._cio_agent.load_database()
        self.redis = self._cio_agent.load_redis()
        self.ai_providers = self._cio_agent.load_ai_providers()
        self.storage = self._cio_agent.load_storage()
        self.finance = self._cfo_agent.load_finance()
        self.production = self._coo_agent.load_production()
        self.hotspot = self._cso_agent.load_hotspot()
        self._sync_flat_attributes()
        return self

    def reload_domain(self, domain: str) -> Any:
        if domain not in DOMAIN_SPECS:
            raise KeyError(f"Unknown configuration domain: {domain}")
        attr_name, model_class = DOMAIN_SPECS[domain]
        value = self._manager.reload_domain(domain=domain, model_class=model_class)
        setattr(self, attr_name, value)
        self._sync_flat_attributes()
        return value

    def invalidate(self, domain: str | None = None) -> None:
        self._manager.invalidate_cache(domain)

    def version(self, domain: str) -> int:
        return self._manager.version(domain)

    def _sync_flat_attributes(self) -> None:
        application = self.application
        database = self.database
        redis = self.redis
        ai = self.ai_providers
        storage = self.storage
        finance = self.finance
        production = self.production
        hotspot = self.hotspot

        flat_values = {
            "APP_NAME": application.app.name,
            "APP_VERSION": application.app.version,
            "DEBUG": application.app.debug,
            "ENV": application.app.env,
            "SERVER_HOST": application.server.host,
            "SERVER_PORT": application.server.port,
            "SERVER_WORKERS": application.server.workers,
            "DATABASE_URL": database.url,
            "DB_POOL_SIZE": database.pool_size,
            "DB_MAX_OVERFLOW": database.max_overflow,
            "DB_POOL_TIMEOUT": database.pool_timeout,
            "DB_ECHO": database.echo,
            "REDIS_HOST": redis.host,
            "REDIS_PORT": redis.port,
            "REDIS_DB": redis.db,
            "REDIS_PASSWORD": redis.password,
            "REDIS_DECODE_RESPONSES": redis.decode_responses,
            "REDIS_URL": redis.build_url(),
            "CELERY_BROKER_URL": redis.build_url(),
            "CELERY_RESULT_BACKEND": redis.build_url(),
            "DEEPSEEK_API_KEY": ai.deepseek.api_key,
            "DEEPSEEK_BASE_URL": ai.deepseek.base_url,
            "DEEPSEEK_MODEL": ai.deepseek.model,
            "GLM_API_KEY": ai.glm.api_key,
            "GLM_BASE_URL": ai.glm.base_url,
            "GLM_MODEL": ai.glm.model,
            "GLM_RESOURCE_ID": ai.glm.resource_id,
            "XFYUN_MAAS_API_KEY": ai.xfyun_maas.api_key,
            "XFYUN_MAAS_BASE_URL": ai.xfyun_maas.base_url,
            "XFYUN_MAAS_MODEL": ai.xfyun_maas.model,
            "XFYUN_MAAS_RESOURCE_ID": ai.xfyun_maas.resource_id,
            "HIDREAM_APP_ID": ai.hidream.app_id,
            "HIDREAM_API_KEY": ai.hidream.api_key,
            "HIDREAM_API_SECRET": ai.hidream.api_secret,
            "HIDREAM_CREATE_URL": ai.hidream.create_url,
            "HIDREAM_QUERY_URL": ai.hidream.query_url,
            "HIDREAM_DEFAULT_RESOLUTION": ai.hidream.default_resolution,
            "HIDREAM_DEFAULT_ASPECT_RATIO": ai.hidream.default_aspect_ratio,
            "SEEDANCE_API_KEY": ai.seedance.api_key,
            "SEEDANCE_BASE_URL": ai.seedance.base_url,
            "SEEDANCE_MODEL": ai.seedance.model,
            "SEEDANCE_RESOURCE_ID": ai.seedance.resource_id,
            "AI_HTTP_TIMEOUT": ai.runtime.http_timeout,
            "AI_MAX_RETRIES": ai.runtime.max_retries,
            "AI_USE_PLACEHOLDER_WHEN_UNCONFIGURED": ai.runtime.use_placeholder_when_unconfigured,
            "VIDEO_STORAGE_BACKEND": storage.video_backend,
            "MEDIA_ROOT": storage.media_root,
            "MEDIA_URL_PREFIX": storage.media_url_prefix,
            "MEDIA_BASE_URL": storage.media_base_url,
            "GITHUB_STORAGE_OWNER": storage.github.owner,
            "GITHUB_STORAGE_REPO": storage.github.repo,
            "GITHUB_STORAGE_TOKEN": storage.github.token,
            "GITHUB_STORAGE_RELEASE_TAG": storage.github.release_tag,
            "IPFS_API_URL": storage.ipfs.api_url,
            "IPFS_GATEWAY_URL": storage.ipfs.gateway_url,
            "IPFS_PIN_ON_ADD": storage.ipfs.pin_on_add,
            "S3_ENDPOINT_URL": storage.s3_compatible.endpoint_url,
            "S3_ACCESS_KEY_ID": storage.s3_compatible.access_key_id,
            "S3_SECRET_ACCESS_KEY": storage.s3_compatible.secret_access_key,
            "S3_BUCKET": storage.s3_compatible.bucket,
            "S3_REGION": storage.s3_compatible.region,
            "S3_OBJECT_PREFIX": storage.s3_compatible.object_prefix,
            "S3_PUBLIC_BASE_URL": storage.s3_compatible.public_base_url,
            "DAILY_BUDGET": finance.daily_budget,
            "COST_WARNING_THRESHOLD": finance.warning_threshold,
            "COST_ALERT_THRESHOLD": finance.alert_threshold,
            "COST_CRITICAL_THRESHOLD": finance.critical_threshold,
            "API_PRICING": finance.api_pricing,
            "DEFAULT_RESOLUTION": production.default_resolution,
            "DEFAULT_FPS": production.default_fps,
            "MAX_VIDEO_DURATION": production.max_video_duration,
            "FFMPEG_PRESET": production.ffmpeg_preset,
            "AUDIO_BITRATE": production.audio_bitrate,
            "VIDEO_BITRATE": production.video_bitrate,
            "MAX_FILE_SIZE": production.max_file_size,
            "HOTSPOT_SCHEDULE": list(hotspot.schedule),
            "HOTSPOT_PLATFORMS": list(hotspot.platforms),
            "HOTSPOT_CATEGORIES": list(hotspot.categories),
            "HOTSPOT_DEFAULT_LIMIT": hotspot.limits.default,
            "HOTSPOT_MAX_LIMIT": hotspot.limits.max,
            "HOTSPOT_MIN_VIEW_COUNT": hotspot.filters.min_view_count,
            "HOTSPOT_MIN_LIKE_COUNT": hotspot.filters.min_like_count,
            "HOTSPOT_RETENTION_DAYS": hotspot.retention_days,
            "LOG_LEVEL": application.logging.level,
            "LOG_FORMAT": application.logging.format,
            "LOG_FILE": application.logging.file,
            "LOG_MAX_BYTES": application.logging.max_bytes,
            "LOG_BACKUP_COUNT": application.logging.backup_count,
            "PROMETHEUS_ENABLED": application.monitoring.prometheus_enabled,
            "METRICS_PORT": application.monitoring.metrics_port,
            "HEALTH_CHECK_INTERVAL": application.monitoring.health_check_interval,
            "CONFIG_DOMAIN_PERMISSIONS": dict(self.permissions.domain_permissions),
            "CONFIG_DYNAMIC_KEYS": list(self.permissions.dynamic_keys),
            "CONFIG_DOMAIN_OWNERS": dict(self.departments.owners),
            "CONTROL_PLANE_MISSION": self.leaders.mission,
            "CONTROL_PLANE_SCOPE": self.leaders.scope,
            "CONTROL_PLANE_LEADERS": {
                name: config.model_dump(mode="python")
                for name, config in self.leaders.leaders.items()
            },
            "WORKFLOW_DEFAULTS": self.workflow.model_dump(mode="python", by_alias=True),
        }
        self.__dict__.update(flat_values)


def get_settings() -> Settings:
    return settings


settings = Settings()

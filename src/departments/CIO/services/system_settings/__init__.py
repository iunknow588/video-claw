from __future__ import annotations

import os
from typing import Any

from departments.CEO.core.config import settings
from departments.CEO.services.control_plane import control_plane
from departments.CIO.services.data_access.system_setting_repository import SystemSettingRepository


DEFAULT_CONSOLE_TITLE = "龙虾宝宝视频制作平台"
DEFAULT_IDENTITY_NAMES: dict[str, str] = {
    "ceo": "龙虾CEO",
    "cao": "龙虾CAO",
    "cmo": "龙虾CMO",
    "cfo": "龙虾CFO",
    "cio": "龙虾CIO",
    "cto": "龙虾CTO",
    "coo": "龙虾COO",
    "cho": "龙虾CHO",
    "cqo": "龙虾CQO",
    "cso": "龙虾CSO",
    "cco": "龙虾CCO",
}

IDENTITY_ORDER: list[str] = [
    "ceo",
    "cao",
    "cmo",
    "cfo",
    "cio",
    "cto",
    "coo",
    "cho",
    "cqo",
    "cso",
    "cco",
]

IDENTITY_SETTING_KEY = "system.identity_names"
CEO_RUNTIME_SETTING_KEY = "system.ceo_runtime_controls"
API_PROVIDER_SETTING_KEY = "system.api_provider_overrides"


class SystemSettingsService:
    """CIO-owned runtime settings service."""

    def __init__(self, session):
        self.repository = SystemSettingRepository(session)

    async def get_system_settings_bundle(self) -> dict[str, Any]:
        return {
            "identity": await self.get_identity_settings(),
            "ceo_runtime": await self.get_ceo_runtime_settings(),
            "api_providers": await self.get_api_provider_settings(),
        }

    async def get_identity_settings(self) -> dict[str, Any]:
        stored_payload = await self._get_payload(IDENTITY_SETTING_KEY)
        stored_names = self._extract_identity_names(stored_payload)

        names: dict[str, str] = {}
        for key in IDENTITY_ORDER:
            value = stored_names.get(key)
            names[key] = self._normalize_name(value) or DEFAULT_IDENTITY_NAMES[key]

        console_title = self._normalize_console_title(stored_payload.get("console_title")) or DEFAULT_CONSOLE_TITLE

        return {
            "console_title": console_title,
            "console_title_default": DEFAULT_CONSOLE_TITLE,
            "names": names,
            "profiles": [
                {
                    "key": key,
                    "code": key.upper(),
                    "name": names[key],
                    "default_name": DEFAULT_IDENTITY_NAMES[key],
                }
                for key in IDENTITY_ORDER
            ],
        }

    async def update_identity_settings(
        self,
        updates: dict[str, Any],
        *,
        console_title: str | None = None,
    ) -> dict[str, Any]:
        current = await self.get_identity_settings()
        names = dict(current["names"])
        for key, value in updates.items():
            if key not in DEFAULT_IDENTITY_NAMES:
                continue
            names[key] = self._normalize_name(value) or DEFAULT_IDENTITY_NAMES[key]

        payload = {
            "console_title": self._normalize_console_title(console_title) or current["console_title"],
            "names": names,
        }
        await self.repository.upsert(setting_key=IDENTITY_SETTING_KEY, payload=payload)
        return await self.get_identity_settings()

    async def get_ceo_runtime_settings(self) -> dict[str, Any]:
        return control_plane.get_runtime_controls()

    async def update_ceo_runtime_settings(self, updates: dict[str, Any]) -> dict[str, Any]:
        current = control_plane.get_runtime_controls()
        payload = {
            "evolution_enabled": current["evolution_enabled"]
            if updates.get("evolution_enabled") is None
            else bool(updates.get("evolution_enabled")),
            "dispatch_mode": str(updates.get("dispatch_mode") or current["dispatch_mode"]).strip() or "graph",
            "qa_rework_max_attempts": int(
                current["qa_rework_max_attempts"]
                if updates.get("qa_rework_max_attempts") is None
                else updates.get("qa_rework_max_attempts")
            ),
            "qa_reroute_strategy": (
                str(updates.get("qa_reroute_strategy") or current["qa_reroute_strategy"]).strip() or "balanced"
            ),
        }
        self._apply_ceo_runtime_payload(payload)
        await self.repository.upsert(setting_key=CEO_RUNTIME_SETTING_KEY, payload=payload)
        return await self.get_ceo_runtime_settings()

    async def get_api_provider_settings(self) -> dict[str, Any]:
        ai = settings.ai_providers
        return {
            "deepseek": self._serialize_provider_profile(ai.deepseek),
            "glm": self._serialize_provider_profile(ai.glm),
            "xfyun_maas": self._serialize_provider_profile(ai.xfyun_maas),
            "hidream": self._serialize_hidream_provider(ai.hidream),
            "seedance": self._serialize_provider_profile(ai.seedance),
            "runtime": {
                "http_timeout": float(ai.runtime.http_timeout),
                "max_retries": int(ai.runtime.max_retries),
                "use_placeholder_when_unconfigured": bool(ai.runtime.use_placeholder_when_unconfigured),
            },
        }

    async def update_api_provider_settings(self, updates: dict[str, Any]) -> dict[str, Any]:
        payload = self._normalize_api_provider_payload(updates)
        self._apply_api_provider_payload(payload)
        await self.repository.upsert(setting_key=API_PROVIDER_SETTING_KEY, payload=payload)
        return await self.get_api_provider_settings()

    async def apply_runtime_overrides(self) -> None:
        ceo_runtime_payload = await self._get_payload(CEO_RUNTIME_SETTING_KEY)
        if ceo_runtime_payload:
            self._apply_ceo_runtime_payload(ceo_runtime_payload)

        api_provider_payload = await self._get_payload(API_PROVIDER_SETTING_KEY)
        if api_provider_payload:
            self._apply_api_provider_payload(api_provider_payload)

    async def _get_payload(self, setting_key: str) -> dict[str, Any]:
        record = await self.repository.get_by_key(setting_key)
        if record and isinstance(record.payload, dict):
            return dict(record.payload)
        return {}

    @staticmethod
    def _extract_identity_names(payload: dict[str, Any]) -> dict[str, Any]:
        names = payload.get("names")
        if isinstance(names, dict):
            return names

        legacy_names = {
            key: value
            for key, value in payload.items()
            if key in DEFAULT_IDENTITY_NAMES and isinstance(value, str)
        }
        return legacy_names

    @staticmethod
    def _serialize_provider_profile(profile: Any) -> dict[str, Any]:
        api_key = str(getattr(profile, "api_key", "") or "")
        base_url = str(getattr(profile, "base_url", "") or "")
        model = str(getattr(profile, "model", "") or "")
        resource_id = str(getattr(profile, "resource_id", "") or "")
        return {
            "api_key": api_key,
            "base_url": base_url,
            "model": model,
            "resource_id": resource_id,
            "configured": bool(api_key.strip() or resource_id.strip()),
        }

    @staticmethod
    def _serialize_hidream_provider(profile: Any) -> dict[str, Any]:
        app_id = str(getattr(profile, "app_id", "") or "")
        api_key = str(getattr(profile, "api_key", "") or "")
        api_secret = str(getattr(profile, "api_secret", "") or "")
        create_url = str(getattr(profile, "create_url", "") or "")
        query_url = str(getattr(profile, "query_url", "") or "")
        return {
            "app_id": app_id,
            "api_key": api_key,
            "api_secret": api_secret,
            "create_url": create_url,
            "query_url": query_url,
            "configured": bool(app_id.strip() or api_key.strip() or api_secret.strip()),
        }

    def _normalize_api_provider_payload(self, updates: dict[str, Any]) -> dict[str, Any]:
        def provider_payload(name: str) -> dict[str, Any]:
            source = updates.get(name) if isinstance(updates.get(name), dict) else {}
            return {
                "api_key": self._normalize_token(source.get("api_key")),
                "base_url": self._normalize_text(source.get("base_url"), limit=320) or "",
                "model": self._normalize_text(source.get("model"), limit=160) or "",
                "resource_id": self._normalize_text(source.get("resource_id"), limit=160) or "",
            }

        hidream_source = updates.get("hidream") if isinstance(updates.get("hidream"), dict) else {}
        runtime_source = updates.get("runtime") if isinstance(updates.get("runtime"), dict) else {}
        return {
            "deepseek": provider_payload("deepseek"),
            "glm": provider_payload("glm"),
            "xfyun_maas": provider_payload("xfyun_maas"),
            "seedance": provider_payload("seedance"),
            "hidream": {
                "app_id": self._normalize_token(hidream_source.get("app_id")),
                "api_key": self._normalize_token(hidream_source.get("api_key")),
                "api_secret": self._normalize_token(hidream_source.get("api_secret")),
                "create_url": self._normalize_text(hidream_source.get("create_url"), limit=320) or "",
                "query_url": self._normalize_text(hidream_source.get("query_url"), limit=320) or "",
            },
            "runtime": {
                "http_timeout": float(runtime_source.get("http_timeout") or 60.0),
                "max_retries": int(runtime_source.get("max_retries") or 2),
                "use_placeholder_when_unconfigured": bool(runtime_source.get("use_placeholder_when_unconfigured")),
            },
        }

    @staticmethod
    def _apply_ceo_runtime_payload(payload: dict[str, Any]) -> None:
        control_plane.update_runtime_controls(
            evolution_enabled=payload.get("evolution_enabled"),
            dispatch_mode=payload.get("dispatch_mode"),
            qa_rework_max_attempts=payload.get("qa_rework_max_attempts"),
            qa_reroute_strategy=payload.get("qa_reroute_strategy"),
        )

    @staticmethod
    def _apply_api_provider_payload(payload: dict[str, Any]) -> None:
        provider_env_map = {
            "deepseek": {
                "api_key": "DEEPSEEK_API_KEY",
                "resource_id": None,
            },
            "glm": {
                "api_key": "GLM_API_KEY",
                "base_url": "GLM_BASE_URL",
                "model": "GLM_MODEL",
                "resource_id": "GLM_RESOURCE_ID",
            },
            "xfyun_maas": {
                "api_key": "XFYUN_MAAS_API_KEY",
                "base_url": "XFYUN_MAAS_BASE_URL",
                "model": "XFYUN_MAAS_MODEL",
                "resource_id": "XFYUN_MAAS_RESOURCE_ID",
            },
            "seedance": {
                "api_key": "SEEDANCE_API_KEY",
                "base_url": "SEEDANCE_BASE_URL",
                "model": "SEEDANCE_MODEL",
                "resource_id": "SEEDANCE_RESOURCE_ID",
            },
        }

        for provider_name, field_map in provider_env_map.items():
            section = payload.get(provider_name) if isinstance(payload.get(provider_name), dict) else {}
            for field_name, env_name in field_map.items():
                if not env_name:
                    continue
                os.environ[env_name] = str(section.get(field_name, "") or "")

        hidream = payload.get("hidream") if isinstance(payload.get("hidream"), dict) else {}
        os.environ["HIDREAM_APP_ID"] = str(hidream.get("app_id", "") or "")
        os.environ["HIDREAM_API_KEY"] = str(hidream.get("api_key", "") or "")
        os.environ["HIDREAM_API_SECRET"] = str(hidream.get("api_secret", "") or "")
        os.environ["HIDREAM_CREATE_URL"] = str(hidream.get("create_url", "") or "")
        os.environ["HIDREAM_QUERY_URL"] = str(hidream.get("query_url", "") or "")

        runtime = payload.get("runtime") if isinstance(payload.get("runtime"), dict) else {}
        os.environ["AI_HTTP_TIMEOUT"] = str(runtime.get("http_timeout", 60.0))
        os.environ["AI_MAX_RETRIES"] = str(runtime.get("max_retries", 2))
        os.environ["AI_USE_PLACEHOLDER_WHEN_UNCONFIGURED"] = (
            "true" if runtime.get("use_placeholder_when_unconfigured", True) else "false"
        )

        settings.reload()

        for provider_name in ("deepseek", "glm", "xfyun_maas", "seedance"):
            provider_payload = payload.get(provider_name) if isinstance(payload.get(provider_name), dict) else {}
            provider = getattr(settings.ai_providers, provider_name)
            provider.api_key = str(provider_payload.get("api_key", "") or "")
            provider.base_url = str(provider_payload.get("base_url", "") or "")
            provider.model = str(provider_payload.get("model", "") or "")
            if hasattr(provider, "resource_id"):
                provider.resource_id = str(provider_payload.get("resource_id", "") or "")

        settings.ai_providers.hidream.app_id = str(hidream.get("app_id", "") or "")
        settings.ai_providers.hidream.api_key = str(hidream.get("api_key", "") or "")
        settings.ai_providers.hidream.api_secret = str(hidream.get("api_secret", "") or "")
        settings.ai_providers.hidream.create_url = str(hidream.get("create_url", "") or "")
        settings.ai_providers.hidream.query_url = str(hidream.get("query_url", "") or "")
        settings.ai_providers.runtime.http_timeout = float(runtime.get("http_timeout", 60.0) or 60.0)
        settings.ai_providers.runtime.max_retries = int(runtime.get("max_retries", 2) or 2)
        settings.ai_providers.runtime.use_placeholder_when_unconfigured = bool(
            runtime.get("use_placeholder_when_unconfigured", True)
        )
        settings._sync_flat_attributes()

    @staticmethod
    def _normalize_name(value: Any) -> str | None:
        normalized = SystemSettingsService._normalize_text(value, limit=40)
        return normalized or None

    @staticmethod
    def _normalize_console_title(value: Any) -> str | None:
        normalized = SystemSettingsService._normalize_text(value, limit=80)
        return normalized or None

    @staticmethod
    def _normalize_token(value: Any) -> str:
        normalized = SystemSettingsService._normalize_text(value, limit=512)
        return normalized or ""

    @staticmethod
    def _normalize_text(value: Any, *, limit: int) -> str | None:
        if not isinstance(value, str):
            return None
        normalized = " ".join(value.strip().split())
        if not normalized:
            return None
        return normalized[:limit]

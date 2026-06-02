from __future__ import annotations

from typing import Any

from departments.CIO.services.data_access.system_setting_repository import SystemSettingRepository


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

SETTING_KEY = "system.identity_names"


class SystemSettingsService:
    """CIO-owned runtime settings service."""

    def __init__(self, session):
        self.repository = SystemSettingRepository(session)

    async def get_identity_settings(self) -> dict[str, Any]:
        record = await self.repository.get_by_key(SETTING_KEY)
        stored_payload = record.payload if record and isinstance(record.payload, dict) else {}

        names: dict[str, str] = {}
        for key in IDENTITY_ORDER:
            value = stored_payload.get(key)
            names[key] = self._normalize_name(value) or DEFAULT_IDENTITY_NAMES[key]

        return {
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

    async def update_identity_settings(self, updates: dict[str, Any]) -> dict[str, Any]:
        current = await self.get_identity_settings()
        names = dict(current["names"])
        for key, value in updates.items():
            if key not in DEFAULT_IDENTITY_NAMES:
                continue
            names[key] = self._normalize_name(value) or DEFAULT_IDENTITY_NAMES[key]

        await self.repository.upsert(setting_key=SETTING_KEY, payload=names)
        return await self.get_identity_settings()

    @staticmethod
    def _normalize_name(value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        normalized = " ".join(value.strip().split())
        if not normalized:
            return None
        return normalized[:40]

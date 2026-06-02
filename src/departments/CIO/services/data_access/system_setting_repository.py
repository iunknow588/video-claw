from __future__ import annotations

from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from departments.CIO.models.system_setting import SystemSettingRecord


class SystemSettingRepository:
    """Centralized repository for CIO-owned system settings."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_key(self, setting_key: str) -> SystemSettingRecord | None:
        result = await self.session.execute(
            select(SystemSettingRecord).where(SystemSettingRecord.setting_key == setting_key)
        )
        return result.scalar_one_or_none()

    async def upsert(self, *, setting_key: str, payload: dict[str, Any]) -> SystemSettingRecord:
        record = await self.get_by_key(setting_key)
        if record is None:
            record = SystemSettingRecord(setting_key=setting_key, payload=jsonable_encoder(payload))
            self.session.add(record)
        else:
            record.payload = jsonable_encoder(payload)
        await self.session.flush()
        return record

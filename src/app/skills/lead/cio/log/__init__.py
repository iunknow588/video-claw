from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.cio import CIOInformationService
from app.skills.base import BaseSkill


class LogSkill(BaseSkill):
    skill_name = "lead.cio.log"
    description = "Records CIO-owned information events and trace annotations."
    parameters_schema = {
        "type": "object",
        "properties": {
            "trace_id": {"type": "string"},
            "level": {"type": "string"},
            "message": {"type": "string"},
            "context": {"type": "object"},
        },
        "required": ["message"],
    }
    tags = ["lead", "cio", "log", "observability"]
    dependencies = ["log.workflow"]
    required_tokens = ["message", "context"]

    def __init__(self, session: AsyncSession | None = None, config: dict[str, Any] | None = None) -> None:
        super().__init__(config=config)
        self.service = CIOInformationService(session)

    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("lead.cio.log must be invoked through async_execute")

    async def async_execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        event = await self.service.record_event(
            trace_id=str(input_data.get("trace_id") or "") or None,
            level=str(input_data.get("level") or "info"),
            message=str(input_data.get("message") or ""),
            context=dict(input_data.get("context") or {}),
        )
        return {"cio_event": event}

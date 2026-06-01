from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.CIO.services.knowledge import CIOInformationService
from app.CEO.skills.base import BaseSkill


class StoreSkill(BaseSkill):
    skill_name = "lead.cio.store"
    description = "Stores workflow artifacts into the CIO-managed lightweight repository."
    parameters_schema = {
        "type": "object",
        "properties": {
            "trace_id": {"type": "string"},
            "artifact_type": {"type": "string"},
            "payload": {"type": "object"},
            "source": {"type": "string"},
        },
        "required": ["trace_id", "artifact_type", "payload"],
    }
    tags = ["lead", "cio", "storage", "repository"]
    dependencies = []
    required_tokens = ["artifact_type", "payload"]

    def __init__(self, session: AsyncSession | None = None, config: dict[str, Any] | None = None) -> None:
        super().__init__(config=config)
        self.service = CIOInformationService(session)

    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("lead.cio.store must be invoked through async_execute")

    async def async_execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        artifact = await self.service.store_artifact(
            trace_id=str(input_data.get("trace_id") or ""),
            artifact_type=str(input_data.get("artifact_type") or ""),
            payload=dict(input_data.get("payload") or {}),
            source=str(input_data.get("source") or "unknown"),
        )
        return {"artifact": artifact}

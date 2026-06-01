from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from departments.CIO.services.knowledge import CIOInformationService
from departments.CEO.skills.base import BaseSkill


class QueryLogSkill(BaseSkill):
    skill_name = "lead.cio.query_log"
    description = "Queries historical workflow logs through the CIO information interface."
    parameters_schema = {
        "type": "object",
        "properties": {
            "trace_id": {"type": "string"},
            "skill_name": {"type": "string"},
            "event_type": {"type": "string"},
            "limit": {"type": "integer"},
        },
        "required": [],
    }
    tags = ["lead", "cio", "log", "query"]
    dependencies = ["lead.cio.log"]
    required_tokens = ["trace_id", "skill_name"]

    def __init__(self, session: AsyncSession | None = None, config: dict[str, Any] | None = None) -> None:
        super().__init__(config=config)
        self.service = CIOInformationService(session)

    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("lead.cio.query_log must be invoked through async_execute")

    async def async_execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        logs = await self.service.query_logs(
            trace_id=str(input_data.get("trace_id") or "") or None,
            skill_name=str(input_data.get("skill_name") or "") or None,
            event_type=str(input_data.get("event_type") or "") or None,
            limit=int(input_data.get("limit") or 20),
        )
        return {"logs": logs}

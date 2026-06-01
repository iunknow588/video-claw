from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.CIO.services.knowledge import CIOInformationService
from app.CEO.skills.base import BaseSkill


class RetrieveSkill(BaseSkill):
    skill_name = "lead.cio.retrieve"
    description = "Retrieves workflow artifacts from the CIO-managed repository."
    parameters_schema = {
        "type": "object",
        "properties": {
            "trace_id": {"type": "string"},
            "artifact_type": {"type": "string"},
            "artifact_id": {"type": "string"},
        },
        "required": [],
    }
    tags = ["lead", "cio", "storage", "repository"]
    dependencies = ["lead.cio.store"]
    required_tokens = ["artifact_type", "artifact_id"]

    def __init__(self, session: AsyncSession | None = None, config: dict[str, Any] | None = None) -> None:
        super().__init__(config=config)
        self.service = CIOInformationService(session)

    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("lead.cio.retrieve must be invoked through async_execute")

    async def async_execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        artifact = await self.service.retrieve_artifact(
            trace_id=str(input_data.get("trace_id") or "") or None,
            artifact_type=str(input_data.get("artifact_type") or "") or None,
            artifact_id=str(input_data.get("artifact_id") or "") or None,
        )
        return {"artifact": artifact}

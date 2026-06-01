from __future__ import annotations

from typing import Any

from app.COO.services.composition import RenderExecutionService
from app.CEO.skills.base import BaseSkill


class RenderExecuteSkill(BaseSkill):
    skill_name = "lead.production.render_execute"
    description = "Turns the composition plan into a delivery-facing render artifact or preview asset."
    parameters_schema = {
        "type": "object",
        "properties": {
            "trace_id": {"type": "string"},
            "platform": {"type": "string"},
            "duration": {"type": "integer"},
            "composition_bundle": {"type": "object"},
            "video_task": {"type": ["object", "null"]},
        },
        "required": ["trace_id", "platform", "duration", "composition_bundle"],
    }
    tags = ["lead", "COO", "render"]
    dependencies = ["lead.production.video_compose_plan"]

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config=config)
        self.service = RenderExecutionService()

    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("lead.production.render_execute must be invoked through async_execute")

    async def async_execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        return await self.service.execute(
            trace_id=str(input_data.get("trace_id") or ""),
            platform=str(input_data.get("platform") or "douyin"),
            duration=int(input_data.get("duration") or 15),
            composition_bundle=dict(input_data.get("composition_bundle") or {}),
            video_task=input_data.get("video_task"),
        )

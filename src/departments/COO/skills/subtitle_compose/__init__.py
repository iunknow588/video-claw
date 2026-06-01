from __future__ import annotations

from typing import Any

from departments.COO.services.asset_management import SubtitleComposerService
from departments.CEO.skills.base import BaseSkill


class SubtitleComposeSkill(BaseSkill):
    skill_name = "lead.production.subtitle_compose"
    description = "Builds a lightweight SRT subtitle asset from approved script scenes and timing hints."
    parameters_schema = {
        "type": "object",
        "properties": {
            "trace_id": {"type": "string"},
            "script": {"type": "object"},
            "target_duration": {"type": "integer"},
        },
        "required": ["script"],
    }
    tags = ["lead", "COO", "subtitle"]
    dependencies = ["lead.production.script_draft"]

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config=config)
        self.service = SubtitleComposerService()

    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        return self.service.compose(
            script=dict(input_data.get("script") or {}),
            trace_id=input_data.get("trace_id"),
            target_duration=input_data.get("target_duration"),
        )

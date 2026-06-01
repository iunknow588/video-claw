from __future__ import annotations

from typing import Any

from departments.COO.services.asset_management import VoiceoverService
from departments.CEO.skills.base import BaseSkill


class VoiceoverGenerateSkill(BaseSkill):
    skill_name = "lead.production.voiceover_generate"
    description = "Generates a lightweight narration asset and SSML plan from the approved script."
    parameters_schema = {
        "type": "object",
        "properties": {
            "trace_id": {"type": "string"},
            "script": {"type": "object"},
            "target_duration": {"type": "integer"},
            "voice_profile": {"type": "string"},
        },
        "required": ["script"],
    }
    tags = ["lead", "COO", "voiceover"]
    dependencies = ["lead.production.script_draft"]

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config=config)
        self.service = VoiceoverService()

    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        return self.service.generate(
            script=dict(input_data.get("script") or {}),
            trace_id=input_data.get("trace_id"),
            target_duration=input_data.get("target_duration"),
            voice_profile=str(input_data.get("voice_profile") or "narrator-neutral"),
        )

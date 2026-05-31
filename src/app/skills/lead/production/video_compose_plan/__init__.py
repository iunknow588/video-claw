from __future__ import annotations

from typing import Any

from app.services.video_composition import VideoCompositionService
from app.skills.base import BaseSkill


class VideoComposePlanSkill(BaseSkill):
    skill_name = "lead.production.video_compose_plan"
    description = "Builds an ffmpeg-friendly composition plan from script, materials, subtitles, and narration."
    parameters_schema = {
        "type": "object",
        "properties": {
            "platform": {"type": "string"},
            "script": {"type": "object"},
            "material_bundle": {"type": "object"},
            "subtitle_bundle": {"type": "object"},
            "voiceover_bundle": {"type": "object"},
            "video_task": {"type": ["object", "null"]},
        },
        "required": ["platform", "script"],
    }
    tags = ["lead", "production", "compose"]
    dependencies = [
        "lead.research.material_search",
        "lead.production.subtitle_compose",
        "lead.production.voiceover_generate",
    ]

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config=config)
        self.service = VideoCompositionService()

    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        return self.service.build_plan(
            platform=str(input_data.get("platform") or "douyin"),
            script=dict(input_data.get("script") or {}),
            material_bundle=dict(input_data.get("material_bundle") or {}),
            subtitle_bundle=dict(input_data.get("subtitle_bundle") or {}),
            voiceover_bundle=dict(input_data.get("voiceover_bundle") or {}),
            video_task=input_data.get("video_task"),
        )

from __future__ import annotations


class VideoProcessSkill:
    skill_name = "lead.production.video_process"

    def run(self, input_bundle: dict) -> dict:
        return {"video_result": input_bundle}


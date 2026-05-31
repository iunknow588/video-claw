from __future__ import annotations


class VideoTaskSkill:
    skill_name = "lead.production.video_task"

    def run(self, input_bundle: dict) -> dict:
        return {"video_task": input_bundle}


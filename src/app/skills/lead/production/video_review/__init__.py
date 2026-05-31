from __future__ import annotations


class VideoReviewSkill:
    skill_name = "lead.production.video_review"

    def run(self, input_bundle: dict) -> dict:
        return {"approved": True, "video_bundle": input_bundle}


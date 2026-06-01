from __future__ import annotations


class PublishPlanSkill:
    skill_name = "lead.publish.publish_plan"

    def run(self, input_bundle: dict) -> dict:
        publish_plan = {
            "platform": input_bundle.get("platform"),
            "publish_goal": input_bundle.get("publish_goal"),
            "audience": input_bundle.get("audience"),
            "video_url": input_bundle.get("video_url"),
            "video_task_id": input_bundle.get("video_task_id"),
            "target_status": "queued",
            "publish_steps": [
                "validate_assets",
                "prepare_platform_payload",
                "submit_publish_request",
                "sync_callback",
            ],
        }
        return {"publish_plan": {**input_bundle, **publish_plan}}

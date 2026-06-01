from __future__ import annotations


class PublishCallbackSkill:
    skill_name = "lead.publish.publish_callback"

    def run(self, input_bundle: dict) -> dict:
        publish_result = input_bundle.get("publish_result", {})
        return {
            "callback_status": "ok",
            "callback_ref": publish_result.get("publish_id"),
            "bundle": input_bundle,
        }

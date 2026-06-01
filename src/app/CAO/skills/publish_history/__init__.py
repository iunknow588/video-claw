from __future__ import annotations


class PublishHistorySkill:
    skill_name = "lead.publish.publish_history"

    def run(self, input_bundle: dict) -> dict:
        return {
            "history_status": "recorded",
            "history_ref": input_bundle.get("callback_ref"),
            "history_bundle": input_bundle,
        }

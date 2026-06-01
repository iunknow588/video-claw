from __future__ import annotations


class PublishExecuteSkill:
    skill_name = "lead.publish.publish_execute"

    def run(self, input_bundle: dict) -> dict:
        publish_result = input_bundle.get("publish_result", {})
        return {
            "publish_result": publish_result,
            "execution_status": publish_result.get("status", "unknown"),
            "execution_bundle": input_bundle,
        }

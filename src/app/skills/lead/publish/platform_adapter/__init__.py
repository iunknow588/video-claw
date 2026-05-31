from __future__ import annotations


class PlatformAdapterSkill:
    skill_name = "lead.publish.platform_adapter"

    def run(self, input_bundle: dict) -> dict:
        publish_plan = input_bundle.get("publish_plan", {})
        platform = publish_plan.get("platform", "unknown")
        return {
            "platform_payload": {
                "platform": platform,
                "adapter_name": f"{platform}_adapter",
                "mode": "stub",
                "request_payload": publish_plan,
            }
        }

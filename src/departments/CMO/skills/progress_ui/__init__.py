from __future__ import annotations

from typing import Any

from departments.CEO.skills.base import BaseSkill
from departments.CMO.services.public_progress import build_public_status_payload


class ProgressUISkill(BaseSkill):
    skill_name = "lead.promotion.progress_ui"
    description = "Formats production workflow stage events into promotion-side progress updates."
    parameters_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["format_status_event"],
            },
            "event": {"type": "object"},
        },
        "required": ["action", "event"],
    }
    tags = ["lead", "promotion", "ui", "progress"]
    dependencies = [
        "lead.cfo.estimate_cost",
        "lead.research",
        "lead.analysis",
        "lead.production",
        "lead.qa",
        "lead.publish",
    ]
    required_tokens = ["event"]

    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        action = input_data.get("action")
        if action != "format_status_event":
            raise ValueError(f"Unsupported action for {self.skill_name}: {action}")

        event = dict(input_data.get("event") or {})
        public_payload = build_public_status_payload(
            str(event.get("stage") or ""),
            str(event.get("status") or ""),
            event.get("message"),
        )
        event["source"] = self.skill_name
        event["actor_key"] = public_payload["actor_key"]
        event["stage_label"] = public_payload["stage_label"]
        event["status_label"] = public_payload["status_label"]
        event["raw_message"] = public_payload["raw_message"]
        event["message"] = public_payload["message"]
        event["channel"] = "promotion_ui"
        return {"event": event}

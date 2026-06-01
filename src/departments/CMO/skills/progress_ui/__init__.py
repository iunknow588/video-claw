from __future__ import annotations

from typing import Any

from departments.CEO.leaders.organization import LEADER_STAGE_LABELS_CN
from departments.CEO.skills.base import BaseSkill


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

    STATUS_LABELS = {
        "running": "执行中",
        "success": "已完成",
        "failed": "失败",
    }

    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        action = input_data.get("action")
        if action != "format_status_event":
            raise ValueError(f"Unsupported action for {self.skill_name}: {action}")

        event = dict(input_data.get("event") or {})
        stage = str(event.get("stage") or "")
        status = str(event.get("status") or "")
        event["source"] = self.skill_name
        event["stage_label"] = LEADER_STAGE_LABELS_CN.get(stage, stage or "未知阶段")
        event["status_label"] = self.STATUS_LABELS.get(status, status or "未知状态")
        event["channel"] = "promotion_ui"
        return {"event": event}

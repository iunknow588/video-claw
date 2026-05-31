from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class LogEvent:
    event_id: str
    ack: bool
    log_ref: str


class LogWorkflowSkill:
    """Run / step / event logger."""

    skill_name = "log.workflow"

    def record(self, payload: dict[str, Any]) -> LogEvent:
        trace_id = str(payload.get("trace_id", ""))
        skill_name = str(payload.get("skill_name", "unknown"))
        return LogEvent(
            event_id=f"{trace_id}:{skill_name}",
            ack=True,
            log_ref="workflow-log",
        )


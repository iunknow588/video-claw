from __future__ import annotations

from typing import Any


class LogAggregator:
    """Builds a normalized structured-log view from workflow events."""

    def aggregate(self, event: Any) -> dict[str, Any]:
        level = self._resolve_level(event)
        message = self._resolve_message(event)
        context = {
            "kind": event.kind,
            "source": event.source,
            "event_type": event.event_type,
            "status": event.status,
            "workflow_run_id": event.workflow_run_id,
            "parent_id": event.parent_id,
            "metadata": dict(event.metadata_json or {}),
        }
        if event.public_payload:
            context["public_payload"] = dict(event.public_payload)
        if event.input_json:
            context["input"] = dict(event.input_json)
        if event.output_json:
            context["output"] = dict(event.output_json)
        if event.error_message:
            context["error_message"] = event.error_message
        if event.kind == "artifact":
            context["artifact_type"] = event.artifact_type
        return {
            "level": level,
            "message": message,
            "context": context,
        }

    def _resolve_level(self, event: Any) -> str:
        if event.level:
            return str(event.level)
        if event.error_message or event.status == "failed" or event.event_type == "fail":
            return "error"
        if event.status == "running":
            return "info"
        return "info"

    def _resolve_message(self, event: Any) -> str:
        if event.message:
            return str(event.message)
        if event.kind == "artifact" and event.artifact_type:
            return f"artifact persisted: {event.artifact_type}"
        return f"{event.source}:{event.event_type}"

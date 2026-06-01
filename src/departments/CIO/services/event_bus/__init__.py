from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from departments.CIO.services.event_bus.event_publisher import EventPublisher, WorkflowEventCallback
from departments.CIO.services.event_bus.event_store import EventStore
from departments.CIO.services.event_bus.event_subscriber import EventSubscriber


@dataclass(slots=True)
class WorkflowEvent:
    trace_id: str
    kind: str
    source: str
    event_type: str
    status: str | None = None
    parent_id: str | None = None
    workflow_run_id: str | None = None
    message: str | None = None
    level: str | None = None
    input_json: dict[str, Any] | None = None
    output_json: dict[str, Any] | None = None
    error_message: str | None = None
    metadata_json: dict[str, Any] | None = None
    artifact_type: str | None = None
    artifact_payload: dict[str, Any] | None = None
    public_payload: dict[str, Any] | None = None
    cost: int = 0


class EventBus:
    """Coordinates event persistence and publication."""

    def __init__(self, event_store: EventStore, event_publisher: EventPublisher):
        self.event_store = event_store
        self.event_publisher = event_publisher

    async def publish(
        self,
        event: WorkflowEvent,
        *,
        event_callback: WorkflowEventCallback | None = None,
    ) -> dict[str, Any]:
        persisted = await self.event_store.persist(event)
        await self.event_publisher.publish(event, event_callback=event_callback)
        return persisted


__all__ = [
    "EventBus",
    "EventPublisher",
    "EventStore",
    "EventSubscriber",
    "WorkflowEvent",
    "WorkflowEventCallback",
]

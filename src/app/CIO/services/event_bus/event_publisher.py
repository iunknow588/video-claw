from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from typing import Any

from app.CIO.services.event_bus.event_subscriber import EventSubscriber

WorkflowEventCallback = Callable[[dict[str, Any]], Awaitable[None] | None]


class EventPublisher:
    """Publishes workflow events to subscribers and optional external callbacks."""

    def __init__(self) -> None:
        self.subscribers: list[EventSubscriber] = []

    def subscribe(self, subscriber: EventSubscriber) -> None:
        self.subscribers.append(subscriber)

    async def publish(
        self,
        event: Any,
        *,
        event_callback: WorkflowEventCallback | None = None,
    ) -> None:
        for subscriber in self.subscribers:
            if not subscriber.matches(event):
                continue
            maybe_awaitable = subscriber.handler(event)
            if inspect.isawaitable(maybe_awaitable):
                await maybe_awaitable

        if not event_callback or not event.public_payload:
            return
        maybe_awaitable = event_callback(dict(event.public_payload))
        if inspect.isawaitable(maybe_awaitable):
            await maybe_awaitable

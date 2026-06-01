from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any


WorkflowEventHandler = Callable[[Any], Awaitable[None] | None]
WorkflowEventPredicate = Callable[[Any], bool]


@dataclass(slots=True)
class EventSubscriber:
    name: str
    handler: WorkflowEventHandler
    predicate: WorkflowEventPredicate = field(default=lambda _event: True)

    def matches(self, event: Any) -> bool:
        return bool(self.predicate(event))

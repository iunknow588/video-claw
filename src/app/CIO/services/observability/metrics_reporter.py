from __future__ import annotations

from collections import Counter
from typing import Any


class MetricsReporter:
    """Collects lightweight in-process counters for workflow events."""

    def __init__(self) -> None:
        self.counters: Counter[str] = Counter()

    async def report(self, event: Any) -> None:
        self.counters[f"kind:{event.kind}"] += 1
        self.counters[f"source:{event.source}"] += 1
        if event.status:
            self.counters[f"status:{event.status}"] += 1

    def snapshot(self) -> dict[str, int]:
        return dict(self.counters)

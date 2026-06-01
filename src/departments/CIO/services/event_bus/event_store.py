from __future__ import annotations

from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession

from departments.CIO.models.artifact import ArtifactRecord
from departments.CIO.models.information_event import InformationEvent
from departments.CIO.services.observability.log_aggregator import LogAggregator


class EventStore:
    """Persists workflow events into CIO-owned event and artifact stores."""

    def __init__(self, session: AsyncSession, log_aggregator: LogAggregator):
        self.session = session
        self.log_aggregator = log_aggregator

    async def persist(self, event: Any) -> dict[str, Any]:
        persisted: dict[str, Any] = {}
        log_record = self.log_aggregator.aggregate(event)
        info_record = InformationEvent(
            trace_id=event.trace_id or None,
            level=str(log_record["level"] or "info"),
            message=str(log_record["message"] or ""),
            context=jsonable_encoder(log_record["context"]),
        )
        self.session.add(info_record)
        await self.session.flush()
        persisted["information_event_id"] = info_record.uuid

        if event.kind == "artifact" and event.artifact_type and event.artifact_payload is not None:
            artifact_record = ArtifactRecord(
                trace_id=event.trace_id,
                artifact_type=event.artifact_type,
                payload=jsonable_encoder(event.artifact_payload),
                source=event.source,
            )
            self.session.add(artifact_record)
            await self.session.flush()
            persisted["artifact_id"] = artifact_record.uuid
        return persisted

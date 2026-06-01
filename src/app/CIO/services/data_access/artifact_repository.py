from __future__ import annotations

from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.CIO.models.artifact import ArtifactRecord
from app.CIO.models.information_event import InformationEvent


class ArtifactRepository:
    """Centralized repository for CIO artifacts and information events."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_artifact(self, payload: dict[str, Any]) -> ArtifactRecord:
        record = ArtifactRecord(**jsonable_encoder(payload))
        self.session.add(record)
        await self.session.flush()
        return record

    async def get_artifact_by_uuid(self, artifact_id: str) -> ArtifactRecord | None:
        result = await self.session.execute(select(ArtifactRecord).where(ArtifactRecord.uuid == artifact_id))
        return result.scalar_one_or_none()

    async def get_latest_artifact(
        self,
        *,
        trace_id: str,
        artifact_type: str | None = None,
    ) -> ArtifactRecord | None:
        query = select(ArtifactRecord).where(ArtifactRecord.trace_id == trace_id)
        if artifact_type:
            query = query.where(ArtifactRecord.artifact_type == artifact_type)
        query = query.order_by(ArtifactRecord.created_at.desc(), ArtifactRecord.id.desc()).limit(1)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def count_artifacts(self) -> int:
        result = await self.session.execute(select(func.count()).select_from(ArtifactRecord))
        return int(result.scalar_one() or 0)

    async def count_distinct_traces(self) -> int:
        result = await self.session.execute(select(func.count(func.distinct(ArtifactRecord.trace_id))))
        return int(result.scalar_one() or 0)

    async def create_information_event(self, payload: dict[str, Any]) -> InformationEvent:
        record = InformationEvent(**jsonable_encoder(payload))
        self.session.add(record)
        await self.session.flush()
        return record

    async def count_information_events(self) -> int:
        result = await self.session.execute(select(func.count()).select_from(InformationEvent))
        return int(result.scalar_one() or 0)

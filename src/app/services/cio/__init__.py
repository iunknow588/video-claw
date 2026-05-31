from __future__ import annotations

from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.artifact import ArtifactRecord
from app.models.information_event import InformationEvent
from app.models.knowledge_asset import KnowledgeAsset
from app.services.workflow_steps import WorkflowStepLogService

DEFAULT_KNOWLEDGE_BASE: dict[str, list[dict[str, Any]]] = {
    "viral_cases": [
        {
            "asset_id": "viral-case-douyin-knowledge",
            "title": "Douyin Knowledge Hook",
            "summary": "Fast hook + quick proof + direct CTA.",
        },
        {
            "asset_id": "viral-case-xhs-lifestyle",
            "title": "Xiaohongshu Lifestyle Contrast",
            "summary": "Scene contrast, practical details, and softer CTA.",
        },
    ],
    "templates": [
        {
            "asset_id": "template-script-clean",
            "title": "Clean Knowledge Script",
            "summary": "Three-beat opening, key insight, closing CTA.",
        },
        {
            "asset_id": "template-qa-report",
            "title": "QA Gate Report",
            "summary": "Pass/fail, failed dimensions, reroute, recommendation.",
        },
    ],
    "platform_guides": [
        {
            "asset_id": "platform-douyin",
            "title": "Douyin Delivery Guide",
            "summary": "Vertical first, stronger opening in first three seconds.",
        },
        {
            "asset_id": "platform-bilibili",
            "title": "Bilibili Delivery Guide",
            "summary": "Longer retention arc, stronger information density.",
        },
    ],
}


class CIOInformationService:
    """Persistent repository, knowledge-base, and log-query service for CIO."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.workflow_step_service = WorkflowStepLogService(session)
        self._defaults_seeded = False

    async def store_artifact(
        self,
        *,
        trace_id: str,
        artifact_type: str,
        payload: dict[str, Any],
        source: str | None = None,
    ) -> dict[str, Any]:
        record = ArtifactRecord(
            trace_id=trace_id,
            artifact_type=artifact_type,
            payload=jsonable_encoder(payload),
            source=source or "unknown",
        )
        self.session.add(record)
        await self.session.flush()
        return self._serialize_artifact(record)

    async def retrieve_artifact(
        self,
        *,
        trace_id: str | None = None,
        artifact_type: str | None = None,
        artifact_id: str | None = None,
    ) -> dict[str, Any] | None:
        if artifact_id:
            result = await self.session.execute(select(ArtifactRecord).where(ArtifactRecord.uuid == artifact_id))
            record = result.scalar_one_or_none()
            return self._serialize_artifact(record) if record else None

        if trace_id and artifact_type:
            result = await self.session.execute(
                select(ArtifactRecord)
                .where(ArtifactRecord.trace_id == trace_id, ArtifactRecord.artifact_type == artifact_type)
                .order_by(ArtifactRecord.created_at.desc(), ArtifactRecord.id.desc())
                .limit(1)
            )
            record = result.scalar_one_or_none()
            return self._serialize_artifact(record) if record else None

        if trace_id:
            result = await self.session.execute(
                select(ArtifactRecord)
                .where(ArtifactRecord.trace_id == trace_id)
                .order_by(ArtifactRecord.created_at.desc(), ArtifactRecord.id.desc())
                .limit(1)
            )
            record = result.scalar_one_or_none()
            return self._serialize_artifact(record) if record else None

        return None

    async def list_knowledge_assets(self, category: str | None = None) -> dict[str, list[dict[str, Any]]]:
        await self._ensure_default_assets()
        query = select(KnowledgeAsset).order_by(KnowledgeAsset.category.asc(), KnowledgeAsset.created_at.asc())
        if category:
            query = query.where(KnowledgeAsset.category == category)
        result = await self.session.execute(query)
        records = list(result.scalars().all())
        grouped: dict[str, list[dict[str, Any]]] = {}
        for record in records:
            grouped.setdefault(record.category, []).append(self._serialize_knowledge_asset(record))
        return grouped if not category else {category: grouped.get(category, [])}

    async def upsert_knowledge_asset(
        self,
        *,
        category: str,
        asset: dict[str, Any],
    ) -> dict[str, Any]:
        await self._ensure_default_assets()
        asset_key = str(asset.get("asset_id") or asset.get("asset_key") or "").strip() or None
        if asset_key:
            result = await self.session.execute(
                select(KnowledgeAsset).where(
                    KnowledgeAsset.category == category,
                    KnowledgeAsset.asset_key == asset_key,
                )
            )
            record = result.scalar_one_or_none()
        else:
            record = None
            asset_key = None

        if record is None:
            record = KnowledgeAsset(
                category=category,
                asset_key=asset_key or f"{category}-{asset.get('title') or 'asset'}",
                title=str(asset.get("title") or asset_key or "Untitled Asset"),
                summary=str(asset.get("summary") or ""),
                payload=jsonable_encoder(asset.get("payload") or {}),
            )
            self.session.add(record)
        else:
            record.title = str(asset.get("title") or record.title)
            record.summary = str(asset.get("summary") or record.summary or "")
            record.payload = jsonable_encoder(asset.get("payload") or record.payload or {})
        await self.session.flush()
        return self._serialize_knowledge_asset(record)

    async def record_event(
        self,
        *,
        trace_id: str | None,
        level: str,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        record = InformationEvent(
            trace_id=trace_id,
            level=level,
            message=message,
            context=jsonable_encoder(context or {}),
        )
        self.session.add(record)
        await self.session.flush()
        return self._serialize_information_event(record)

    async def query_logs(
        self,
        *,
        trace_id: str | None = None,
        skill_name: str | None = None,
        event_type: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        steps = await self.workflow_step_service.list_steps(
            limit=limit,
            trace_id=trace_id,
            skill_name=skill_name,
            event_type=event_type,
        )
        return [
            {
                "trace_id": item.trace_id,
                "skill_name": item.skill_name,
                "event_type": item.event_type,
                "status": item.status,
                "error_message": item.error_message,
                "created_at": item.created_at,
            }
            for item in steps
        ]

    async def build_summary(self) -> dict[str, int]:
        await self._ensure_default_assets()
        artifact_count = await self._count_rows(ArtifactRecord)
        event_count = await self._count_rows(InformationEvent)
        knowledge_count = await self._count_rows(KnowledgeAsset)
        trace_bucket_result = await self.session.execute(select(func.count(func.distinct(ArtifactRecord.trace_id))))
        log_record_count = len(await self.workflow_step_service.list_steps(limit=1000))

        return {
            "artifact_count": artifact_count,
            "trace_bucket_count": int(trace_bucket_result.scalar_one() or 0),
            "knowledge_asset_count": knowledge_count,
            "event_buffer_count": event_count,
            "log_record_count": log_record_count,
        }

    async def _count_rows(self, model: type[Any]) -> int:
        result = await self.session.execute(select(func.count()).select_from(model))
        return int(result.scalar_one() or 0)

    async def _ensure_default_assets(self) -> None:
        if self._defaults_seeded:
            return
        result = await self.session.execute(select(func.count()).select_from(KnowledgeAsset))
        if int(result.scalar_one() or 0) == 0:
            for category, assets in DEFAULT_KNOWLEDGE_BASE.items():
                for asset in assets:
                    self.session.add(
                        KnowledgeAsset(
                            category=category,
                            asset_key=str(asset.get("asset_id") or ""),
                            title=str(asset.get("title") or ""),
                            summary=str(asset.get("summary") or ""),
                            payload=jsonable_encoder(asset.get("payload") or {}),
                        )
                    )
            await self.session.flush()
        self._defaults_seeded = True

    def _serialize_artifact(self, record: ArtifactRecord) -> dict[str, Any]:
        return {
            "artifact_id": record.uuid,
            "trace_id": record.trace_id,
            "artifact_type": record.artifact_type,
            "payload": dict(record.payload or {}),
            "source": record.source,
            "created_at": record.created_at,
        }

    def _serialize_information_event(self, record: InformationEvent) -> dict[str, Any]:
        return {
            "event_id": record.uuid,
            "trace_id": record.trace_id,
            "level": record.level,
            "message": record.message,
            "context": dict(record.context or {}),
            "created_at": record.created_at,
        }

    def _serialize_knowledge_asset(self, record: KnowledgeAsset) -> dict[str, Any]:
        return {
            "asset_id": record.asset_key,
            "title": record.title,
            "summary": record.summary,
            "payload": dict(record.payload or {}),
            "updated_at": record.updated_at,
        }

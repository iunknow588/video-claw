from __future__ import annotations

from typing import Any

from departments.CIO.services.data_access.artifact_repository import ArtifactRepository
from departments.CIO.services.data_access.knowledge_repository import KnowledgeRepository
from departments.CIO.services.workflow_steps import WorkflowStepLogService

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

    def __init__(self, session):
        self.session = session
        self.workflow_step_service = WorkflowStepLogService(session)
        self.artifact_repository = ArtifactRepository(session)
        self.knowledge_repository = KnowledgeRepository(session)
        self._defaults_seeded = False

    async def store_artifact(
        self,
        *,
        trace_id: str,
        artifact_type: str,
        payload: dict[str, Any],
        source: str | None = None,
    ) -> dict[str, Any]:
        record = await self.artifact_repository.create_artifact(
            {
                "trace_id": trace_id,
                "artifact_type": artifact_type,
                "payload": payload,
                "source": source or "unknown",
            }
        )
        return self._serialize_artifact(record)

    async def retrieve_artifact(
        self,
        *,
        trace_id: str | None = None,
        artifact_type: str | None = None,
        artifact_id: str | None = None,
    ) -> dict[str, Any] | None:
        if artifact_id:
            record = await self.artifact_repository.get_artifact_by_uuid(artifact_id)
            return self._serialize_artifact(record) if record else None
        if trace_id:
            record = await self.artifact_repository.get_latest_artifact(trace_id=trace_id, artifact_type=artifact_type)
            return self._serialize_artifact(record) if record else None
        return None

    async def list_knowledge_assets(self, category: str | None = None) -> dict[str, list[dict[str, Any]]]:
        await self._ensure_default_assets()
        records = await self.knowledge_repository.list_assets(category=category)
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
        record = (
            await self.knowledge_repository.get_by_category_key(category=category, asset_key=asset_key)
            if asset_key
            else None
        )
        if record is None:
            record = await self.knowledge_repository.create_asset(
                {
                    "category": category,
                    "asset_key": asset_key or f"{category}-{asset.get('title') or 'asset'}",
                    "title": str(asset.get("title") or asset_key or "Untitled Asset"),
                    "summary": str(asset.get("summary") or ""),
                    "payload": asset.get("payload") or {},
                }
            )
        else:
            record = await self.knowledge_repository.update_asset(
                record,
                {
                    "title": str(asset.get("title") or record.title),
                    "summary": str(asset.get("summary") or record.summary or ""),
                    "payload": asset.get("payload") or record.payload or {},
                },
            )
        return self._serialize_knowledge_asset(record)

    async def record_event(
        self,
        *,
        trace_id: str | None,
        level: str,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        record = await self.artifact_repository.create_information_event(
            {
                "trace_id": trace_id,
                "level": level,
                "message": message,
                "context": context or {},
            }
        )
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
        artifact_count = await self.artifact_repository.count_artifacts()
        event_count = await self.artifact_repository.count_information_events()
        knowledge_count = await self.knowledge_repository.count_assets()
        trace_bucket_count = await self.artifact_repository.count_distinct_traces()
        log_record_count = len(await self.workflow_step_service.list_steps(limit=1000))
        return {
            "artifact_count": artifact_count,
            "trace_bucket_count": trace_bucket_count,
            "knowledge_asset_count": knowledge_count,
            "event_buffer_count": event_count,
            "log_record_count": log_record_count,
        }

    async def _ensure_default_assets(self) -> None:
        if self._defaults_seeded:
            return
        if await self.knowledge_repository.count_assets() == 0:
            for category, assets in DEFAULT_KNOWLEDGE_BASE.items():
                for asset in assets:
                    await self.knowledge_repository.create_asset(
                        {
                            "category": category,
                            "asset_key": str(asset.get("asset_id") or ""),
                            "title": str(asset.get("title") or ""),
                            "summary": str(asset.get("summary") or ""),
                            "payload": asset.get("payload") or {},
                        }
                    )
        self._defaults_seeded = True

    def _serialize_artifact(self, record) -> dict[str, Any]:
        return {
            "artifact_id": record.uuid,
            "trace_id": record.trace_id,
            "artifact_type": record.artifact_type,
            "payload": dict(record.payload or {}),
            "source": record.source,
            "created_at": record.created_at,
        }

    def _serialize_information_event(self, record) -> dict[str, Any]:
        return {
            "event_id": record.uuid,
            "trace_id": record.trace_id,
            "level": record.level,
            "message": record.message,
            "context": dict(record.context or {}),
            "created_at": record.created_at,
        }

    def _serialize_knowledge_asset(self, record) -> dict[str, Any]:
        return {
            "asset_id": record.asset_key,
            "title": record.title,
            "summary": record.summary,
            "payload": dict(record.payload or {}),
            "updated_at": record.updated_at,
        }

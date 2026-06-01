from __future__ import annotations

from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from departments.CIO.models.step_log import WorkflowStepLog
from departments.CIO.models.workflow import WorkflowRun


class WorkflowRepository:
    """Centralized repository for CIO-owned workflow runs and step logs."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_run(self, payload: dict[str, Any]) -> WorkflowRun:
        record = WorkflowRun(**jsonable_encoder(payload))
        self.session.add(record)
        await self.session.flush()
        return record

    async def update_run(self, record: WorkflowRun, updates: dict[str, Any]) -> WorkflowRun:
        for key, value in jsonable_encoder(updates).items():
            setattr(record, key, value)
        await self.session.flush()
        return record

    async def list_runs(
        self,
        *,
        limit: int = 50,
        domain: str | None = None,
        platform: str | None = None,
        status: str | None = None,
    ) -> list[WorkflowRun]:
        query = select(WorkflowRun).order_by(WorkflowRun.created_at.desc()).limit(limit)
        if domain:
            query = query.where(WorkflowRun.domain == domain)
        if platform:
            query = query.where(WorkflowRun.platform == platform)
        if status:
            query = query.where(WorkflowRun.status == status)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_run_by_uuid(self, workflow_run_id: str) -> WorkflowRun | None:
        result = await self.session.execute(select(WorkflowRun).where(WorkflowRun.uuid == workflow_run_id))
        return result.scalar_one_or_none()

    async def create_step(self, payload: dict[str, Any]) -> WorkflowStepLog:
        record = WorkflowStepLog(**jsonable_encoder(payload))
        self.session.add(record)
        await self.session.flush()
        return record

    async def list_steps(
        self,
        *,
        limit: int = 200,
        trace_id: str | None = None,
        skill_name: str | None = None,
        event_type: str | None = None,
        ascending: bool = False,
    ) -> list[WorkflowStepLog]:
        order_clause = WorkflowStepLog.created_at.asc() if ascending else WorkflowStepLog.created_at.desc()
        query = select(WorkflowStepLog).order_by(order_clause, WorkflowStepLog.id.asc()).limit(limit)
        if trace_id:
            query = query.where(WorkflowStepLog.trace_id == trace_id)
        if skill_name:
            query = query.where(WorkflowStepLog.skill_name == skill_name)
        if event_type:
            query = query.where(WorkflowStepLog.event_type == event_type)
        result = await self.session.execute(query)
        return list(result.scalars().all())

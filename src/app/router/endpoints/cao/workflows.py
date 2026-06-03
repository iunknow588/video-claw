"""
Workflow API endpoints.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from departments.CEO.services.orchestration.domain_workflow import DomainWorkflowService
from departments.CEO.skills.registry import ensure_builtin_skills_registered, registry
from departments.CIO.db.session import get_db
from departments.CIO.schemas.video import (
    DomainWorkflowRequest,
    DomainWorkflowResponse,
    SkillDescriptorResponse,
    WorkflowRunResponse,
    WorkflowStepLogResponse,
    WorkflowTraceResponse,
)
from departments.CIO.services.scheduler import TriggerService
from departments.CIO.services.workflow_runs import WorkflowRunService
from departments.CIO.services.workflow_steps import WorkflowStepLogService

router = APIRouter(prefix="/workflows", tags=["workflows"])


class TriggerRequestPayload(BaseModel):
    """Request to create a scheduled trigger."""

    name: str = Field(..., description="Trigger name")
    cron: str = Field(..., description="Cron expression (e.g. '0 3 * * *')")
    domain: str = Field(..., description="Domain for workflow")
    platform: str = Field(..., description="Platform for workflow")
    input: Optional[Dict[str, Any]] = Field(None, description="Workflow input parameters")
    enabled: bool = Field(True, description="Is trigger enabled")


class UpdateTriggerRequest(BaseModel):
    """Request to update a trigger."""

    name: Optional[str] = None
    cron: Optional[str] = None
    domain: Optional[str] = None
    platform: Optional[str] = None
    input: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None


class TriggerResponse(BaseModel):
    """Trigger response."""

    uuid: str
    name: str
    cron: str
    domain: str
    platform: str
    input_params: Optional[Dict[str, Any]]
    enabled: bool
    last_fired_at: Optional[datetime]
    next_fire_at: Optional[datetime]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


def _build_trigger_response(trigger) -> TriggerResponse:
    return TriggerResponse(
        uuid=trigger.uuid,
        name=trigger.name,
        cron=trigger.cron,
        domain=trigger.domain,
        platform=trigger.platform,
        input_params=trigger.input_params,
        enabled=trigger.enabled,
        last_fired_at=trigger.last_fired_at,
        next_fire_at=trigger.next_fire_at,
        created_at=trigger.created_at,
        updated_at=trigger.updated_at,
    )


@router.get("/skills", response_model=List[SkillDescriptorResponse])
async def list_workflow_skills():
    ensure_builtin_skills_registered()
    return registry.list_descriptors()


@router.post("/runs", response_model=DomainWorkflowResponse)
async def create_workflow_run(
    request: DomainWorkflowRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await DomainWorkflowService(db).run(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/runs", response_model=List[WorkflowRunResponse])
async def list_workflow_runs(
    domain: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    trigger_id: Optional[str] = Query(None, description="Filter by trigger ID"),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    service = WorkflowRunService(db)
    if trigger_id:
        return await service.get_runs_by_trigger(trigger_id, status=status, limit=limit)
    return await service.list_runs(limit=limit, domain=domain, platform=platform, status=status)


@router.get("/steps", response_model=List[WorkflowStepLogResponse])
async def list_workflow_steps(
    trace_id: Optional[str] = Query(None),
    skill_name: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    return await WorkflowStepLogService(db).list_steps(
        limit=limit,
        trace_id=trace_id,
        skill_name=skill_name,
        event_type=event_type,
    )


@router.get("/runs/{workflow_run_id}/trace", response_model=WorkflowTraceResponse)
async def get_workflow_trace(
    workflow_run_id: str,
    db: AsyncSession = Depends(get_db),
):
    run_service = WorkflowRunService(db)
    step_service = WorkflowStepLogService(db)
    run = await run_service.get_by_uuid(workflow_run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")

    trace_id = getattr(run, "trace_id", None)
    if isinstance(run.result_payload, dict):
        trace_id = trace_id or run.result_payload.get("trace_id")

    steps = await step_service.list_steps(limit=500, trace_id=trace_id) if trace_id else []
    summary = await step_service.summarize_trace(trace_id) if trace_id else {"trace_id": None, "step_count": 0}
    summary = dict(summary or {})
    summary["trigger_id"] = getattr(run, "trigger_id", None)
    return {
        "run": run,
        "steps": steps,
        "summary": summary,
    }


@router.get("/triggers", response_model=List[TriggerResponse])
async def list_triggers(
    enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
    limit: int = Query(100, ge=1, le=1000),
):
    service = TriggerService()
    triggers = await service.list_triggers(enabled=enabled, limit=limit)
    return [_build_trigger_response(trigger) for trigger in triggers]


@router.post("/triggers", response_model=TriggerResponse)
async def create_trigger(request: TriggerRequestPayload):
    service = TriggerService()
    trigger = await service.create_trigger(
        name=request.name,
        cron=request.cron,
        domain=request.domain,
        platform=request.platform,
        input_params=request.input,
        enabled=request.enabled,
    )
    return _build_trigger_response(trigger)


@router.get("/triggers/{trigger_id}", response_model=TriggerResponse)
async def get_trigger(trigger_id: str):
    service = TriggerService()
    trigger = await service.get_trigger(trigger_id)
    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")
    return _build_trigger_response(trigger)


@router.patch("/triggers/{trigger_id}", response_model=TriggerResponse)
async def update_trigger(trigger_id: str, request: UpdateTriggerRequest):
    service = TriggerService()
    updates = request.model_dump(exclude_unset=True)
    if "input" in updates:
        updates["input_params"] = updates.pop("input")
    trigger = await service.update_trigger(trigger_id, **updates)
    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")
    return _build_trigger_response(trigger)


@router.delete("/triggers/{trigger_id}")
async def delete_trigger(trigger_id: str):
    service = TriggerService()
    success = await service.delete_trigger(trigger_id)
    if not success:
        raise HTTPException(status_code=404, detail="Trigger not found")
    return {"message": "Trigger deleted successfully"}

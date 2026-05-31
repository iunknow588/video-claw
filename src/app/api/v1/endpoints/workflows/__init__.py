"""
Domain-driven workflow endpoints.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.video import (
    DomainWorkflowRequest,
    DomainWorkflowResponse,
    SkillDescriptorResponse,
    WorkflowRunResponse,
    WorkflowTraceResponse,
    WorkflowStepLogResponse,
)
from app.services.workflow import DomainWorkflowService
from app.services.workflow_runs import WorkflowRunService
from app.services.workflow_steps import WorkflowStepLogService
from app.skills.catalog import ensure_builtin_skills_registered
from app.skills.registry import registry

router = APIRouter()


@router.get("/skills", response_model=List[SkillDescriptorResponse])
async def list_registered_skills():
    """List framework-managed skill descriptors for discovery and orchestration."""
    ensure_builtin_skills_registered()
    return registry.list_descriptors()


@router.post("/domain-auto-run", response_model=DomainWorkflowResponse)
async def run_domain_workflow(
    data: DomainWorkflowRequest,
    db: AsyncSession = Depends(get_db),
):
    """Run an automated domain workflow from hotspot collection to optional video generation."""
    service = DomainWorkflowService(db)
    try:
        return await service.run(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/runs", response_model=List[WorkflowRunResponse])
async def list_workflow_runs(
    limit: int = Query(50, ge=1, le=200),
    domain: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List historical workflow execution records."""
    service = WorkflowRunService(db)
    return await service.list_runs(limit=limit, domain=domain, platform=platform, status=status)


@router.get("/steps", response_model=List[WorkflowStepLogResponse])
async def list_workflow_steps(
    limit: int = Query(200, ge=1, le=500),
    trace_id: Optional[str] = Query(None),
    skill_name: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List step-level workflow logs."""
    service = WorkflowStepLogService(db)
    return await service.list_steps(limit=limit, trace_id=trace_id, skill_name=skill_name, event_type=event_type)


@router.get("/runs/{workflow_run_id}/trace", response_model=WorkflowTraceResponse)
async def get_workflow_trace(
    workflow_run_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a workflow run together with its step-level trace."""
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
    return {"run": run, "steps": steps, "summary": summary}

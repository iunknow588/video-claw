from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from departments.CAO.services.use_cases.workflow_gateway import WorkflowGatewayUseCase
from departments.CIO.db.session import get_db
from departments.CIO.schemas.video import (
    DomainWorkflowRequest,
    DomainWorkflowResponse,
    SkillDescriptorResponse,
    WorkflowRunResponse,
    WorkflowStepLogResponse,
    WorkflowTraceResponse,
)

router = APIRouter(prefix="/workflows")


@router.get("/skills", response_model=List[SkillDescriptorResponse])
async def list_registered_skills(
    db: AsyncSession = Depends(get_db),
):
    return await WorkflowGatewayUseCase(db).list_registered_skills()


@router.post("/domain-auto-run", response_model=DomainWorkflowResponse)
async def run_domain_workflow(
    data: DomainWorkflowRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await WorkflowGatewayUseCase(db).run_domain_workflow(data)
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
    return await WorkflowGatewayUseCase(db).list_workflow_runs(
        limit=limit,
        domain=domain,
        platform=platform,
        status=status,
    )


@router.get("/steps", response_model=List[WorkflowStepLogResponse])
async def list_workflow_steps(
    limit: int = Query(200, ge=1, le=500),
    trace_id: Optional[str] = Query(None),
    skill_name: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await WorkflowGatewayUseCase(db).list_workflow_steps(
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
    try:
        return await WorkflowGatewayUseCase(db).get_workflow_trace(workflow_run_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

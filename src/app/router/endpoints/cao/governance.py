from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from departments.CAO.services.use_cases.governance_gateway import GovernanceGatewayUseCase
from departments.CIO.db.session import get_db
from departments.CIO.schemas.video import (
    GovernanceBudgetRequest,
    GovernanceConditionalEdgeRequest,
    GovernanceLeaderCreateRequest,
    GovernanceLeaderProposalRequest,
    GovernanceLeaderUpdateRequest,
    GovernanceOptimizeCommandRequest,
    GovernanceReportCollectRequest,
    GovernanceResourceAdjustRequest,
    GovernanceRollbackRequest,
    GovernanceWorkflowEdgeRequest,
    GovernanceWorkflowUpdateRequest,
)

router = APIRouter(prefix="/governance")


@router.get("/company-status")
async def get_company_status(
    db: AsyncSession = Depends(get_db),
):
    return await GovernanceGatewayUseCase(db).get_company_status()


@router.get("/workflow")
async def get_workflow(
    db: AsyncSession = Depends(get_db),
):
    return await GovernanceGatewayUseCase(db).get_workflow()


@router.post("/workflow")
async def set_workflow(
    data: GovernanceWorkflowUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await GovernanceGatewayUseCase(db).set_workflow(data.graph_definition)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/workflow/edges")
async def add_workflow_edge(
    data: GovernanceWorkflowEdgeRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await GovernanceGatewayUseCase(db).add_edge(data.from_leader, data.to_leader)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/workflow/conditional-edges")
async def add_workflow_conditional_edge(
    data: GovernanceConditionalEdgeRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await GovernanceGatewayUseCase(db).add_conditional_edge(
            data.from_leader,
            data.router_func,
            data.mapping,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/leaders")
async def list_leaders(
    db: AsyncSession = Depends(get_db),
):
    return await GovernanceGatewayUseCase(db).list_leaders()


@router.post("/leaders")
async def add_leader(
    data: GovernanceLeaderCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await GovernanceGatewayUseCase(db).add_leader(data.name, data.config)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/leaders/{leader_name}")
async def get_leader_status(
    leader_name: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await GovernanceGatewayUseCase(db).get_leader_status(leader_name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/leaders/{leader_name}")
async def update_leader(
    leader_name: str,
    data: GovernanceLeaderUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await GovernanceGatewayUseCase(db).update_leader_config(leader_name, data.config)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/leaders/{leader_name}")
async def remove_leader(
    leader_name: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await GovernanceGatewayUseCase(db).remove_leader(leader_name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/leaders/{leader_name}/rollback")
async def rollback_leader(
    leader_name: str,
    data: GovernanceRollbackRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await GovernanceGatewayUseCase(db).rollback_leader(leader_name, data.version)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/leaders/{leader_name}/optimize")
async def issue_leader_optimize_command(
    leader_name: str,
    data: GovernanceOptimizeCommandRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await GovernanceGatewayUseCase(db).issue_optimize_command(
            leader_name=leader_name,
            target_metric=data.target_metric,
            goal_value=data.goal_value,
            note=data.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/leaders/{leader_name}/request-report")
async def request_leader_report(
    leader_name: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await GovernanceGatewayUseCase(db).request_leader_report(leader_name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/leaders/{leader_name}/reports/latest")
async def get_latest_leader_report(
    leader_name: str,
    report_type: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await GovernanceGatewayUseCase(db).get_latest_leader_report(
            leader_name=leader_name,
            report_type=report_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/leaders/{leader_name}/reports")
async def list_reports_for_leader(
    leader_name: str,
    report_type: str | None = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    return await GovernanceGatewayUseCase(db).list_leader_reports(
        leader_name=leader_name,
        report_type=report_type,
        limit=limit,
    )


@router.post("/leaders/{leader_name}/approve-change")
async def approve_leader_change(
    leader_name: str,
    data: GovernanceLeaderProposalRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await GovernanceGatewayUseCase(db).approve_leader_change(leader_name, data.proposal)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/leaders/{leader_name}/budget")
async def set_leader_budget(
    leader_name: str,
    data: GovernanceBudgetRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await GovernanceGatewayUseCase(db).set_leader_budget(leader_name, data.token_limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/leaders/{leader_name}/resources")
async def adjust_leader_resources(
    leader_name: str,
    data: GovernanceResourceAdjustRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await GovernanceGatewayUseCase(db).adjust_resource_allocation(
            leader_name,
            data.resource_type,
            data.amount,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/tasks/{workflow_run_id}/progress")
async def get_task_progress(
    workflow_run_id: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await GovernanceGatewayUseCase(db).get_task_progress(workflow_run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/evolution/enable")
async def enable_evolution(
    db: AsyncSession = Depends(get_db),
):
    return await GovernanceGatewayUseCase(db).enable_evolution()


@router.post("/evolution/disable")
async def disable_evolution(
    db: AsyncSession = Depends(get_db),
):
    return await GovernanceGatewayUseCase(db).disable_evolution()


@router.post("/evolution/cycle")
async def run_evolution_cycle(
    db: AsyncSession = Depends(get_db),
):
    return await GovernanceGatewayUseCase(db).evolution_cycle()


@router.post("/reports/collect")
async def collect_periodic_reports(
    data: GovernanceReportCollectRequest,
    db: AsyncSession = Depends(get_db),
):
    return await GovernanceGatewayUseCase(db).collect_periodic_reports(cadence=data.cadence)


@router.get("/reports")
async def list_all_leader_reports(
    leader_name: str | None = None,
    report_type: str | None = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    return await GovernanceGatewayUseCase(db).list_leader_reports(
        leader_name=leader_name,
        report_type=report_type,
        limit=limit,
    )

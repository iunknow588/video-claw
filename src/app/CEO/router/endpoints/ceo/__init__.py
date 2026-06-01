from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.CEO.services.use_cases.ceo_control_api import CEOControlApiUseCase
from app.CIO.db.session import get_db
from app.CIO.schemas.video import (
    CEOBudgetRequest,
    CEOChatRequest,
    CEOConditionalEdgeRequest,
    CEOLeaderCreateRequest,
    CEOLeaderProposalRequest,
    CEOLeaderUpdateRequest,
    CEOOptimizeCommandRequest,
    CEOReportCollectRequest,
    CEOResourceAdjustRequest,
    CEORollbackRequest,
    CEOWorkflowEdgeRequest,
    CEOWorkflowUpdateRequest,
)
from app.CMO.services.use_cases.chat_stream import ChatStreamUseCase

router = APIRouter()


@router.post("/chat")
async def chat_with_ceo(
    data: CEOChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """CEO governance chat gateway implemented by the CMO communication service."""
    return StreamingResponse(
        ChatStreamUseCase(db).stream_user_message(data.message),
        media_type="application/x-ndjson",
    )


@router.get("/company-status")
async def get_company_status(
    db: AsyncSession = Depends(get_db),
):
    return await CEOControlApiUseCase(db).get_company_status()


@router.get("/workflow")
async def get_ceo_workflow(
    db: AsyncSession = Depends(get_db),
):
    return await CEOControlApiUseCase(db).get_workflow()


@router.post("/workflow")
async def set_ceo_workflow(
    data: CEOWorkflowUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await CEOControlApiUseCase(db).set_workflow(data.graph_definition)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/workflow/edges")
async def add_workflow_edge(
    data: CEOWorkflowEdgeRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await CEOControlApiUseCase(db).add_edge(data.from_leader, data.to_leader)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/workflow/conditional-edges")
async def add_workflow_conditional_edge(
    data: CEOConditionalEdgeRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await CEOControlApiUseCase(db).add_conditional_edge(
            data.from_leader,
            data.router_func,
            data.mapping,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/leaders")
async def list_ceo_leaders(
    db: AsyncSession = Depends(get_db),
):
    return await CEOControlApiUseCase(db).list_leaders()


@router.post("/leaders")
async def add_ceo_leader(
    data: CEOLeaderCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await CEOControlApiUseCase(db).add_leader(data.name, data.config)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/leaders/{leader_name}")
async def get_ceo_leader_status(
    leader_name: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await CEOControlApiUseCase(db).get_leader_status(leader_name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/leaders/{leader_name}")
async def update_ceo_leader(
    leader_name: str,
    data: CEOLeaderUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await CEOControlApiUseCase(db).update_leader_config(leader_name, data.config)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/leaders/{leader_name}")
async def remove_ceo_leader(
    leader_name: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await CEOControlApiUseCase(db).remove_leader(leader_name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/leaders/{leader_name}/rollback")
async def rollback_ceo_leader(
    leader_name: str,
    data: CEORollbackRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await CEOControlApiUseCase(db).rollback_leader(leader_name, data.version)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/leaders/{leader_name}/optimize")
async def issue_leader_optimize_command(
    leader_name: str,
    data: CEOOptimizeCommandRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await CEOControlApiUseCase(db).issue_optimize_command(
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
        return await CEOControlApiUseCase(db).request_leader_report(leader_name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/leaders/{leader_name}/reports/latest")
async def get_latest_leader_report(
    leader_name: str,
    report_type: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await CEOControlApiUseCase(db).get_latest_leader_report(
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
    return await CEOControlApiUseCase(db).list_leader_reports(
        leader_name=leader_name,
        report_type=report_type,
        limit=limit,
    )


@router.post("/leaders/{leader_name}/approve-change")
async def approve_leader_change(
    leader_name: str,
    data: CEOLeaderProposalRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await CEOControlApiUseCase(db).approve_leader_change(leader_name, data.proposal)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/leaders/{leader_name}/budget")
async def set_leader_budget(
    leader_name: str,
    data: CEOBudgetRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await CEOControlApiUseCase(db).set_leader_budget(leader_name, data.token_limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/leaders/{leader_name}/resources")
async def adjust_leader_resources(
    leader_name: str,
    data: CEOResourceAdjustRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await CEOControlApiUseCase(db).adjust_resource_allocation(
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
        return await CEOControlApiUseCase(db).get_task_progress(workflow_run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/evolution/enable")
async def enable_evolution(
    db: AsyncSession = Depends(get_db),
):
    return await CEOControlApiUseCase(db).enable_evolution()


@router.post("/evolution/disable")
async def disable_evolution(
    db: AsyncSession = Depends(get_db),
):
    return await CEOControlApiUseCase(db).disable_evolution()


@router.post("/evolution/cycle")
async def run_evolution_cycle(
    db: AsyncSession = Depends(get_db),
):
    return await CEOControlApiUseCase(db).evolution_cycle()


@router.post("/reports/collect")
async def collect_periodic_reports(
    data: CEOReportCollectRequest,
    db: AsyncSession = Depends(get_db),
):
    return await CEOControlApiUseCase(db).collect_periodic_reports(cadence=data.cadence)


@router.get("/reports")
async def list_all_leader_reports(
    leader_name: str | None = None,
    report_type: str | None = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    return await CEOControlApiUseCase(db).list_leader_reports(
        leader_name=leader_name,
        report_type=report_type,
        limit=limit,
    )

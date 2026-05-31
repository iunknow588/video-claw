from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.CAO.service import CAOConsoleService
from app.db.session import get_db

router = APIRouter()


@router.get("/pipeline-status")
async def get_cao_pipeline_status(
    db: AsyncSession = Depends(get_db),
):
    service = CAOConsoleService(db)
    return await service.get_pipeline_status()


@router.get("/runs")
async def list_cao_public_runs(
    limit: int = Query(8, ge=1, le=50),
    domain: str | None = Query(None),
    platform: str | None = Query(None),
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    service = CAOConsoleService(db)
    return await service.list_public_runs(limit=limit, domain=domain, platform=platform, status=status)


@router.get("/runs/{workflow_run_id}/trace")
async def get_cao_public_trace(
    workflow_run_id: str,
    db: AsyncSession = Depends(get_db),
):
    service = CAOConsoleService(db)
    try:
        return await service.get_public_trace(workflow_run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

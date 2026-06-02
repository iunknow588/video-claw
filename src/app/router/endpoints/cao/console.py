from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from departments.CAO.services.use_cases.public_console import PublicConsoleUseCase
from departments.CIO.db.session import get_db
from departments.CIO.schemas.system_settings import IdentitySettingsUpdateRequest

router = APIRouter()


@router.get("/pipeline-status")
async def get_cao_pipeline_status(
    db: AsyncSession = Depends(get_db),
):
    return await PublicConsoleUseCase(db).get_pipeline_status()


@router.get("/runs")
async def list_cao_public_runs(
    limit: int = Query(8, ge=1, le=50),
    domain: str | None = Query(None),
    platform: str | None = Query(None),
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await PublicConsoleUseCase(db).list_public_runs(
        limit=limit,
        domain=domain,
        platform=platform,
        status=status,
    )


@router.get("/runs/{workflow_run_id}/trace")
async def get_cao_public_trace(
    workflow_run_id: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await PublicConsoleUseCase(db).get_public_trace(workflow_run_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/identity-settings")
async def get_cao_identity_settings(
    db: AsyncSession = Depends(get_db),
):
    return await PublicConsoleUseCase(db).get_identity_settings()


@router.patch("/identity-settings")
async def update_cao_identity_settings(
    data: IdentitySettingsUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    return await PublicConsoleUseCase(db).update_identity_settings(data.names)

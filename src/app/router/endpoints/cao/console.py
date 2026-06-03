from __future__ import annotations

from fastapi import APIRouter, Depends
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

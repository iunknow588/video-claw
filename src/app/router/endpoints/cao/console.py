from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from departments.CAO.services.use_cases.public_console import PublicConsoleUseCase
from departments.CIO.db.session import get_db
from departments.CIO.schemas.system_settings import (
    APIProviderSettingsUpdateRequest,
    CEORuntimeSettingsUpdateRequest,
    IdentitySettingsUpdateRequest,
)

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


@router.get("/system-settings")
async def get_cao_system_settings(
    db: AsyncSession = Depends(get_db),
):
    return await PublicConsoleUseCase(db).get_system_settings()


@router.patch("/system-settings/identity")
async def update_cao_identity_profile(
    data: IdentitySettingsUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    return await PublicConsoleUseCase(db).update_identity_profile(
        console_title=data.console_title,
        names=data.names,
    )


@router.get("/system-settings/ceo-runtime")
async def get_cao_ceo_runtime_settings(
    db: AsyncSession = Depends(get_db),
):
    return await PublicConsoleUseCase(db).get_ceo_runtime_settings()


@router.patch("/system-settings/ceo-runtime")
async def update_cao_ceo_runtime_settings(
    data: CEORuntimeSettingsUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    return await PublicConsoleUseCase(db).update_ceo_runtime_settings(data.model_dump())


@router.get("/system-settings/api-providers")
async def get_cao_api_provider_settings(
    db: AsyncSession = Depends(get_db),
):
    return await PublicConsoleUseCase(db).get_api_provider_settings()


@router.patch("/system-settings/api-providers")
async def update_cao_api_provider_settings(
    data: APIProviderSettingsUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    return await PublicConsoleUseCase(db).update_api_provider_settings(data.model_dump())

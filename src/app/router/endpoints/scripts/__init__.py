"""
Scripts API endpoints.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from departments.CIO.db.session import get_db
from departments.CIO.schemas.video import ScriptCreate, ScriptResponse, ScriptReviewRequest
from departments.COO.services.use_cases.script_api import ScriptApiUseCase

router = APIRouter()


@router.post("", response_model=ScriptResponse)
async def create_script(
    data: ScriptCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await ScriptApiUseCase(db).create_script(data)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("", response_model=list[ScriptResponse])
async def list_scripts(
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await ScriptApiUseCase(db).list_scripts(status=status)


@router.post("/review/{script_id}", response_model=ScriptResponse)
async def review_script(
    script_id: str,
    data: ScriptReviewRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await ScriptApiUseCase(db).review_script(
            script_id,
            approved=data.approved,
            feedback=data.feedback,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

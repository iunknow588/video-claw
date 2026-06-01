"""
Scripts API endpoints.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.CIO.db.session import get_db
from app.CIO.schemas.video import ScriptCreate, ScriptResponse, ScriptReviewRequest
from app.COO.services.use_cases.script_api import ScriptApiUseCase

router = APIRouter()


@router.post("", response_model=ScriptResponse)
async def create_script(
    data: ScriptCreate,
    db: AsyncSession = Depends(get_db),
):
    """Generate new script from analysis."""
    try:
        return await ScriptApiUseCase(db).create_script(data)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("")
async def list_scripts(
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List scripts."""
    return await ScriptApiUseCase(db).list_scripts(status=status)


@router.post("/review/{script_id}")
async def review_script(
    script_id: str,
    data: ScriptReviewRequest,
    db: AsyncSession = Depends(get_db),
):
    """Review and approve or reject script."""
    try:
        return await ScriptApiUseCase(db).review_script(
            script_id,
            approved=data.approved,
            feedback=data.feedback,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

"""
Scripts API Endpoints
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.services.script import ScriptService
from app.schemas.video import ScriptCreate, ScriptResponse, ScriptReviewRequest
from app.models.analysis import AnalysisReport
from app.models.script import Script
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("", response_model=ScriptResponse)
async def create_script(
    data: ScriptCreate,
    db: AsyncSession = Depends(get_db),
):
    """Generate new script from analysis"""
    # Get analysis
    result = await db.execute(select(AnalysisReport).where(AnalysisReport.uuid == data.analysis_id))
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    service = ScriptService(db)
    script = await service.generate_script(
        analysis=analysis,
        content_type=data.content_type,
        style=data.style,
        topic=data.topic,
        duration=data.duration,
    )
    return script


@router.get("")
async def list_scripts(
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List scripts"""
    query = select(Script).order_by(Script.created_at.desc())
    if status:
        query = query.where(Script.status == status)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/review/{script_id}")
async def review_script(
    script_id: str,
    data: ScriptReviewRequest,
    db: AsyncSession = Depends(get_db),
):
    """Review and approve/reject script"""
    service = ScriptService(db)
    try:
        script = await service.review_script(script_id, data.approved, data.feedback)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return script

"""
Analysis API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from departments.CCO.services.use_cases.analysis_api import AnalysisApiUseCase
from departments.CIO.db.session import get_db
from departments.CIO.schemas.video import AnalysisCreate, AnalysisResponse

router = APIRouter()


@router.post("", response_model=AnalysisResponse)
async def create_analysis(
    data: AnalysisCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create AI analysis for a hotspot."""
    try:
        return await AnalysisApiUseCase(db).create_analysis(data)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/hotspot/{hotspot_id}")
async def get_analysis_by_hotspot(
    hotspot_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get analysis by hotspot ID."""
    try:
        return await AnalysisApiUseCase(db).get_analysis_by_hotspot(hotspot_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

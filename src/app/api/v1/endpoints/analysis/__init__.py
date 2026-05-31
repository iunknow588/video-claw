"""
Analysis API Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.analysis import AIAnalysisService
from app.schemas.video import AnalysisCreate, AnalysisResponse
from app.models.hotspot import HotspotItem
from app.core.logging import get_logger
from sqlalchemy import select

logger = get_logger(__name__)
router = APIRouter()


@router.post("", response_model=AnalysisResponse)
async def create_analysis(
    data: AnalysisCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create AI analysis for a hotspot"""
    # Get hotspot
    result = await db.execute(select(HotspotItem).where(HotspotItem.uuid == data.hotspot_id))
    hotspot = result.scalar_one_or_none()
    if not hotspot:
        raise HTTPException(status_code=404, detail="Hotspot not found")
    
    service = AIAnalysisService(db)
    report = await service.analyze_content(hotspot)
    return report


@router.get("/hotspot/{hotspot_id}")
async def get_analysis_by_hotspot(
    hotspot_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get analysis by hotspot ID"""
    from app.models.analysis import AnalysisReport
    result = await db.execute(
        select(AnalysisReport).where(AnalysisReport.hotspot_id == hotspot_id)
        .order_by(AnalysisReport.created_at.desc())
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return report
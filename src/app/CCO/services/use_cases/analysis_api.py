from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.CCO.services.content_creation import AIAnalysisService
from app.CIO.models.analysis import AnalysisReport
from app.CIO.schemas.video import AnalysisCreate
from app.CIO.services.data_access import AnalysisRepository, HotspotRepository


class AnalysisApiUseCase:
    """API-facing analysis use case owned by CCO."""

    def __init__(self, session: AsyncSession):
        self.analysis_service = AIAnalysisService(session)
        self.analysis_repository = AnalysisRepository(session)
        self.hotspot_repository = HotspotRepository(session)

    async def create_analysis(self, data: AnalysisCreate) -> AnalysisReport:
        hotspot = await self.hotspot_repository.get_by_uuid(data.hotspot_id)
        if not hotspot:
            raise LookupError("Hotspot not found")
        return await self.analysis_service.analyze_content(hotspot)

    async def get_analysis_by_hotspot(self, hotspot_id: str) -> AnalysisReport:
        reports = await self.analysis_repository.list_by_hotspot(hotspot_id, limit=1)
        report = reports[0] if reports else None
        if not report:
            raise LookupError("Analysis not found")
        return report

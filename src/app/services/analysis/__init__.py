"""
AI Analysis Service
Uses DeepSeek for content reverse engineering
"""

from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import AnalysisReport
from app.models.hotspot import HotspotItem
from app.core.config import settings
from app.core.logging import get_logger
from app.services.ai_clients import AIProviderError, DeepSeekClient
from app.services.audit import AuditService

logger = get_logger(__name__)


class AIAnalysisService:
    """Service for AI-powered content analysis"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.api_key = settings.DEEPSEEK_API_KEY
        self.base_url = settings.DEEPSEEK_BASE_URL
        self.model = settings.DEEPSEEK_MODEL
        self.audit_service = AuditService(session)
        self.client = DeepSeekClient(api_key=self.api_key, base_url=self.base_url)
    
    async def analyze_content(self, hotspot: HotspotItem) -> AnalysisReport:
        """Analyze hotspot content using DeepSeek-V4"""
        
        prompt = self._build_analysis_prompt(hotspot)
        
        # TODO: Implement actual API call to DeepSeek
        # For MVP, return structured placeholder
        analysis_data = await self._call_deepseek(prompt)
        
        report = AnalysisReport(
            hotspot_id=hotspot.uuid,
            analysis_type="comprehensive",
            content_structure=analysis_data.get("content_structure", {}),
            emotion_curve=analysis_data.get("emotion_curve", {}),
            hook_design=analysis_data.get("hook_design", {}),
            framework_summary=analysis_data.get("framework_summary", ""),
            reusable_elements=analysis_data.get("reusable_elements", []),
            risk_warnings=analysis_data.get("risk_warnings", []),
            api_cost=analysis_data.get("cost", 0.0),
        )
        report._token_usage = analysis_data.get("token_usage", {})  # type: ignore[attr-defined]
        
        self.session.add(report)
        await self.session.flush()
        await self.audit_service.record_cost(
            source_type="analysis",
            source_uuid=report.uuid,
            provider="deepseek",
            model_name=self.model,
            amount=float(report.api_cost or 0.0),
            request_summary=prompt[:500],
            metadata_json={
                "hotspot_id": hotspot.uuid,
                "analysis_type": report.analysis_type,
                "token_usage": analysis_data.get("token_usage", {}),
            },
        )
        logger.info("Analysis completed", uuid=report.uuid, hotspot_id=hotspot.uuid)
        return report
    
    def _build_analysis_prompt(self, hotspot: HotspotItem) -> str:
        """Build analysis prompt for DeepSeek"""
        return f"""
Analyze the following viral video content and provide structured insights:

Title: {hotspot.title}
Author: {hotspot.author}
Platform: {hotspot.platform}
Views: {hotspot.view_count}
Likes: {hotspot.like_count}
Comments: {hotspot.comment_count}
Category: {hotspot.category}

Provide analysis in JSON format with these keys:
- content_structure: narrative structure breakdown
- emotion_curve: emotional progression mapping
- hook_design: hook techniques used
- framework_summary: reusable framework description
- reusable_elements: list of reusable elements
- risk_warnings: potential copyright/ethical risks
"""
    
    async def _call_deepseek(self, prompt: str) -> Dict[str, Any]:
        """Call DeepSeek API with placeholder fallback when not configured."""
        logger.info("Calling DeepSeek API", model=self.model, configured=self.client.is_configured)
        if not self.client.is_configured and settings.AI_USE_PLACEHOLDER_WHEN_UNCONFIGURED:
            return self._placeholder_response()

        try:
            response = await self.client.chat_json(model=self.model, prompt=prompt)
            return {
                "content_structure": response.data.get("content_structure", {}),
                "emotion_curve": response.data.get("emotion_curve", {}),
                "hook_design": response.data.get("hook_design", {}),
                "framework_summary": response.data.get("framework_summary", ""),
                "reusable_elements": response.data.get("reusable_elements", []),
                "risk_warnings": response.data.get("risk_warnings", []),
                "cost": float(response.data.get("cost", 0.0)),
                "token_usage": response.usage.to_dict(),
            }
        except (AIProviderError, KeyError, TypeError, ValueError) as exc:
            logger.warning("DeepSeek call fallback to placeholder", error=str(exc))
            if settings.AI_USE_PLACEHOLDER_WHEN_UNCONFIGURED:
                return self._placeholder_response()
            raise

    def _placeholder_response(self) -> Dict[str, Any]:
        return {
            "content_structure": {},
            "emotion_curve": {},
            "hook_design": {},
            "framework_summary": "Placeholder analysis",
            "reusable_elements": [],
            "risk_warnings": ["Copyright check required"],
            "cost": 0.05,
            "token_usage": self.client.normalize_usage(None, prompt="placeholder-analysis", completion_text="Placeholder analysis").to_dict(),
        }

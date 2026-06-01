"""
Script Generation Service
Uses GLM-5.1 for original script creation
"""

from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from departments.CIO.models.script import Script
from departments.CIO.models.analysis import AnalysisReport
from departments.CEO.core.logging import get_logger
from departments.CTO.services.ai_clients import (
    AIProviderError,
    build_glm_client,
    get_ai_provider_config,
    should_use_placeholder,
)
from departments.CQO.services.audit import AuditService

logger = get_logger(__name__)


class ScriptService:
    """Service for generating video scripts"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.provider = get_ai_provider_config("glm")
        self.model = self.provider.model
        self.audit_service = AuditService(session)
        self.client = build_glm_client(self.provider)
    
    async def generate_script(
        self,
        analysis: AnalysisReport,
        content_type: str,
        style: str,
        topic: str,
        duration: int = 60,
    ) -> Script:
        """Generate original script based on analysis"""
        
        prompt = self._build_script_prompt(analysis, content_type, style, topic, duration)
        
        script_data = await self._call_glm(prompt)
        
        script = Script(
            analysis_id=analysis.uuid,
            content_type=content_type,
            style=style,
            topic=topic,
            title=script_data.get("title", "Untitled"),
            duration=duration,
            scenes=script_data.get("scenes", []),
            hook=script_data.get("hook", ""),
            cta=script_data.get("cta", ""),
            tags=script_data.get("tags", []),
            version=1,
            status="pending_review",
            similarity_score=script_data.get("similarity_score", 0.0),
            api_cost=script_data.get("cost", 0.0),
        )
        script._token_usage = script_data.get("token_usage", {})  # type: ignore[attr-defined]
        
        self.session.add(script)
        await self.session.flush()
        await self.audit_service.record_cost(
            source_type="script",
            source_uuid=script.uuid,
            provider="glm",
            model_name=self.model,
            amount=float(script.api_cost or 0.0),
            request_summary=prompt[:500],
            metadata_json={
                "analysis_id": analysis.uuid,
                "topic": topic,
                "token_usage": script_data.get("token_usage", {}),
            },
        )
        logger.info("Script generated", uuid=script.uuid, topic=topic)
        return script
    
    def _build_script_prompt(
        self,
        analysis: AnalysisReport,
        content_type: str,
        style: str,
        topic: str,
        duration: int,
    ) -> str:
        """Build script generation prompt"""
        return f"""
Based on the following viral content analysis, create an original video script:

Framework: {analysis.framework_summary}
Reusable Elements: {analysis.reusable_elements}

Requirements:
- Content Type: {content_type}
- Style: {style}
- Topic: {topic}
- Duration: {duration} seconds
- Must be original and distinct from the analyzed content
- Similarity score should be below 0.3

Provide output in JSON format:
- title: script title
- scenes: array of scene objects with timing, visuals, audio, text
- hook: opening hook text
- cta: call to action
- tags: relevant tags
- similarity_score: estimated similarity to original (0-1)
"""
    
    async def _call_glm(self, prompt: str) -> Dict[str, Any]:
        """Call GLM API with placeholder fallback when not configured."""
        logger.info("Calling GLM API", model=self.model, configured=self.client.is_configured)
        if should_use_placeholder(self.provider):
            return self._placeholder_response()

        try:
            response = await self.client.chat_json(model=self.model, prompt=prompt)
            return {
                "title": response.data.get("title", "Untitled"),
                "scenes": response.data.get("scenes", []),
                "hook": response.data.get("hook", ""),
                "cta": response.data.get("cta", ""),
                "tags": response.data.get("tags", []),
                "similarity_score": float(response.data.get("similarity_score", 0.0)),
                "cost": float(response.data.get("cost", 0.0)),
                "token_usage": response.usage.to_dict(),
            }
        except (AIProviderError, KeyError, TypeError, ValueError) as exc:
            logger.warning("GLM call fallback to placeholder", error=str(exc))
            if should_use_placeholder(self.provider):
                return self._placeholder_response()
            raise

    def _placeholder_response(self) -> Dict[str, Any]:
        return {
            "title": "Generated Script",
            "scenes": [
                {
                    "timing": "0-8s",
                    "visuals": "Open with an eye-catching close-up and fast pacing",
                    "audio": "Narration sets the problem and promise",
                    "text": "Hook and problem statement",
                },
                {
                    "timing": "8-35s",
                    "visuals": "Explain the core workflow with concrete examples",
                    "audio": "Narration breaks down the method step by step",
                    "text": "Main value delivery",
                },
                {
                    "timing": "35-60s",
                    "visuals": "Summarize takeaways and call for follow-up action",
                    "audio": "Narration closes with a memorable CTA",
                    "text": "Summary and CTA",
                },
            ],
            "hook": "Three steps to turn a hot topic into a usable video idea.",
            "cta": "Follow for more!",
            "tags": ["mvp", "ai-video"],
            "similarity_score": 0.2,
            "cost": 0.08,
            "token_usage": self.client.normalize_usage(None, prompt="placeholder-script", completion_text="Generated Script").to_dict(),
        }
    
    async def review_script(self, script_id: str, approved: bool, feedback: str = "") -> Script:
        """Review and approve/reject script"""
        from sqlalchemy import select
        result = await self.session.execute(select(Script).where(Script.uuid == script_id))
        script = result.scalar_one_or_none()
        if not script:
            raise ValueError(f"Script {script_id} not found")

        status_before = script.status
        script.status = "approved" if approved else "rejected"
        if feedback:
            script.cta = f"{script.cta}\n\nReview Feedback:\n{feedback}".strip()
        await self.audit_service.record_review(
            item_type="script",
            item_uuid=script.uuid,
            stage="script_review",
            approved=approved,
            feedback=feedback,
            status_before=status_before,
            status_after=script.status,
            review_payload={"analysis_id": script.analysis_id},
        )
        logger.info("Script reviewed", uuid=script_id, approved=approved)
        return script

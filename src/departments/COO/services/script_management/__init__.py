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
    build_xfyun_maas_client,
    get_ai_provider_config,
    should_use_placeholder,
)
from departments.CQO.services.audit import AuditService

logger = get_logger(__name__)


class ScriptService:
    """Service for generating video scripts"""
    CONTENT_TYPE_LABELS = {
        "knowledge": "知识讲解类",
        "news": "热点口播类",
        "review": "测评对比类",
        "story": "剧情演绎类",
        "product": "种草推荐类",
    }
    STYLE_LABELS = {
        "clean": "专业干净",
        "fast": "快节奏",
        "story": "剧情感",
        "dynamic": "动态节奏",
        "realistic": "写实",
        "cinematic": "电影感",
    }
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.provider = get_ai_provider_config("xfyun_maas")
        self.model = self.provider.model
        self.audit_service = AuditService(session)
        self.client = build_xfyun_maas_client(self.provider)
    
    async def generate_script(
        self,
        analysis: AnalysisReport,
        content_type: str,
        style: str,
        topic: str,
        duration: int = 60,
        audience: str | None = None,
        publish_goal: str | None = None,
    ) -> Script:
        """Generate original script based on analysis"""

        prompt = self._build_script_prompt(
            analysis,
            content_type,
            style,
            topic,
            duration,
            audience=audience,
            publish_goal=publish_goal,
        )
        
        script_data = await self._call_text_generation(
            prompt,
            topic=topic,
            content_type=content_type,
            duration=duration,
            audience=audience,
            publish_goal=publish_goal,
        )
        normalized_scenes = self._normalize_scenes(script_data.get("scenes", []))
        
        script = Script(
            analysis_id=analysis.uuid,
            content_type=content_type,
            style=style,
            topic=topic,
            title=script_data.get("title", "Untitled"),
            duration=duration,
            scenes=normalized_scenes,
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
            provider=self.provider.provider,
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
        *,
        audience: str | None = None,
        publish_goal: str | None = None,
    ) -> str:
        """Build script generation prompt"""
        content_type_label = self.CONTENT_TYPE_LABELS.get(content_type, content_type)
        style_label = self.STYLE_LABELS.get(style, style)
        audience_line = f"- Target Audience: {audience}\n" if audience else ""
        goal_line = f"- Publish Goal: {publish_goal}\n" if publish_goal else ""
        structure_guidance = self._build_structure_guidance(content_type)
        return f"""
Based on the following viral content analysis, create an original video script:

Framework: {analysis.framework_summary}
Reusable Elements: {analysis.reusable_elements}

Requirements:
- Content Type: {content_type_label}
- Style: {style_label}
- Topic: {topic}
- Duration: {duration} seconds
{audience_line}{goal_line}- Keep the script aligned with the requested video type
- Must be original and distinct from the analyzed content
- Similarity score should be below 0.3
- Return title, hook, CTA, scene text, and narration in Simplified Chinese

Creative guidance:
{structure_guidance}

Provide output in JSON format:
- title: script title
- scenes: array of scene objects with timing, visuals, audio, text
- hook: opening hook text
- cta: call to action
- tags: relevant tags
- similarity_score: estimated similarity to original (0-1)
"""

    def _build_structure_guidance(self, content_type: str) -> str:
        guidance_map = {
            "knowledge": "- Use a clear teaching hook, three-step explanation, and a practical takeaway.",
            "news": "- Start with the newest point first, keep rhythm fast, and summarize the key update clearly.",
            "review": "- Highlight comparison dimensions, real pros and cons, and a decisive recommendation.",
            "story": "- Build a conflict, turn, and payoff with stronger emotional continuity between scenes.",
            "product": "- Emphasize selling points, real use scenarios, and a strong conversion-oriented CTA.",
        }
        return guidance_map.get(content_type, "- Keep the structure concise, clear, and easy to follow.")
    
    async def _call_text_generation(
        self,
        prompt: str,
        *,
        topic: str,
        content_type: str,
        duration: int,
        audience: str | None,
        publish_goal: str | None,
    ) -> Dict[str, Any]:
        """Call the configured text provider with placeholder fallback when not configured."""
        logger.info("Calling XFYun MaaS API", model=self.model, configured=self.client.is_configured)
        if should_use_placeholder(self.provider):
            return self._placeholder_response(
                topic=topic,
                content_type=content_type,
                duration=duration,
                audience=audience,
                publish_goal=publish_goal,
            )

        try:
            response = await self.client.chat_json(
                model=self.model,
                prompt=prompt,
                system_prompt="You generate original short-video scripts. Return valid JSON only.",
                temperature=0.7,
            )
            return {
                "title": response.data.get("title", "Untitled"),
                "scenes": self._normalize_scenes(response.data.get("scenes", [])),
                "hook": response.data.get("hook", ""),
                "cta": response.data.get("cta", ""),
                "tags": response.data.get("tags", []),
                "similarity_score": float(response.data.get("similarity_score", 0.0)),
                "cost": float(response.data.get("cost", 0.0)),
                "token_usage": response.usage.to_dict(),
            }
        except (AIProviderError, KeyError, TypeError, ValueError) as exc:
            logger.warning("XFYun MaaS call fallback to placeholder", error=str(exc))
            if should_use_placeholder(self.provider):
                return self._placeholder_response(
                    topic=topic,
                    content_type=content_type,
                    duration=duration,
                    audience=audience,
                    publish_goal=publish_goal,
                )
            raise

    def _placeholder_response(
        self,
        *,
        topic: str,
        content_type: str,
        duration: int,
        audience: str | None,
        publish_goal: str | None,
    ) -> Dict[str, Any]:
        title_map = {
            "knowledge": f"{topic}，先抓这3个关键动作",
            "news": f"{topic}，最新变化先看这3点",
            "review": f"{topic}，到底该怎么选",
            "story": f"{topic}，一线门店最真实的冲突",
            "product": f"{topic}，为什么更容易被顾客记住",
        }
        audience_text = audience or "目标用户"
        goal_text = publish_goal or "提升内容转化"
        first_scene_end = max(8, min(12, max(duration // 5, 8)))
        second_scene_end = max(first_scene_end + 12, min(duration - 10, int(duration * 0.7)))
        if second_scene_end >= duration:
            second_scene_end = max(first_scene_end + 8, duration - 8)
        return {
            "title": title_map.get(content_type, f"{topic}内容拆解"),
            "scenes": self._normalize_scenes([
                {
                    "timing": f"0-{first_scene_end}s",
                    "visuals": f"门店现场或问题场景快速切入，突出“{topic}”里最常见的误区。",
                    "audio": f"先抛出问题：为什么很多人做{topic}，看起来很忙，结果却不稳定？",
                    "text": f"{topic}最容易做错的，往往不是努力不够，而是顺序没排对。",
                },
                {
                    "timing": f"{first_scene_end}-{second_scene_end}s",
                    "visuals": "用步骤卡点、数字提示和前后对比，拆出2到3个可执行动作。",
                    "audio": f"第二段给方法：先讲关键动作，再讲常见坑点，最后补充一个适合{audience_text}落地的判断标准。",
                    "text": "拆成步骤讲清楚，观众才会愿意看完，也更容易记住重点。",
                },
                {
                    "timing": f"{second_scene_end}-{duration}s",
                    "visuals": "收束到结果感和行动建议，镜头回到门店经营核心画面。",
                    "audio": f"最后总结：围绕“{goal_text}”，真正该先优化的，不是做更多内容，而是把每个动作讲得更具体。",
                    "text": "先收藏这条，后面继续拆更细的执行动作。",
                },
            ]),
            "hook": f"{topic}这件事，很多门店不是不会做，而是一开始就做反了。",
            "cta": "先收藏这条，后面继续拆更细的执行动作。",
            "tags": [self.CONTENT_TYPE_LABELS.get(content_type, content_type), "实操拆解", "门店运营"],
            "similarity_score": 0.2,
            "cost": 0.08,
            "token_usage": self.client.normalize_usage(
                None,
                prompt="placeholder-script",
                completion_text="structured placeholder script",
            ).to_dict(),
        }

    @staticmethod
    def _normalize_scenes(raw_scenes: Any) -> list[dict[str, str | None]]:
        if not isinstance(raw_scenes, list):
            return []

        normalized: list[dict[str, str | None]] = []
        for item in raw_scenes:
            if not isinstance(item, dict):
                continue
            timing = item.get("timing") or item.get("time") or item.get("timestamp")
            visuals = item.get("visuals") or item.get("visual") or item.get("shot")
            audio = item.get("audio") or item.get("voiceover") or item.get("narration")
            text = item.get("text") or item.get("overlay") or item.get("caption")
            normalized.append(
                {
                    "timing": str(timing).strip() if timing is not None else None,
                    "visuals": str(visuals).strip() if visuals is not None else None,
                    "audio": str(audio).strip() if audio is not None else None,
                    "text": str(text).strip() if text is not None else None,
                }
            )
        return normalized
    
    async def review_script(self, script_id: str, approved: bool, feedback: str = "") -> Script:
        """Review and approve/reject script"""
        from sqlalchemy import select
        result = await self.session.execute(select(Script).where(Script.uuid == script_id))
        script = result.scalar_one_or_none()
        if not script:
            raise ValueError(f"Script {script_id} not found")

        status_before = script.status
        script.status = "approved" if approved else "rejected"
        if feedback and feedback.strip() != "Auto-approved by workflow.":
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
        await self.session.flush()
        await self.session.refresh(script)
        logger.info("Script reviewed", uuid=script_id, approved=approved)
        return script

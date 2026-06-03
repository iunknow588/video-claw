"""
Video Generation Service
Uses Seedance 2.0 for AI video generation
"""

import asyncio
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from departments.CIO.models.video import VideoTask
from departments.CIO.models.script import Script
from departments.CEO.core.logging import get_logger
from departments.CTO.services.ai_clients import (
    AIProviderError,
    build_seedance_client,
    get_ai_provider_config,
    should_use_placeholder,
)
from departments.CQO.services.audit import AuditService
from departments.CIO.services.storage import (
    build_placeholder_video_bytes,
    download_video_bytes,
    get_video_storage,
    get_storage_runtime,
)

logger = get_logger(__name__)


class VideoService:
    """Service for AI video generation"""
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
    PLATFORM_LABELS = {
        "douyin": "抖音",
        "xiaohongshu": "小红书",
        "xigua": "西瓜视频",
        "bilibili": "B站",
    }
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.provider = get_ai_provider_config("seedance")
        self.model = self.provider.model
        self.audit_service = AuditService(session)
        self.storage_runtime = get_storage_runtime()
        self.storage = get_video_storage(self.storage_runtime)
        self.client = build_seedance_client(self.provider)
    
    async def create_task(
        self,
        script: Script,
        style: str,
        size: str = "1080x1920",
        platform: str | None = None,
    ) -> VideoTask:
        """Create video generation task"""

        prompt = self._build_video_prompt(script, style, platform=platform)
        
        task = VideoTask(
            script_id=script.uuid,
            status="pending",
            style=style,
            size=size,
            duration=script.duration,
            prompt=prompt,
            progress=0.0,
        )
        
        self.session.add(task)
        await self.session.flush()
        logger.info("Video task created", uuid=task.uuid, script_id=script.uuid)
        return task
    
    def _build_video_prompt(self, script: Script, style: str, *, platform: str | None = None) -> str:
        """Build video generation prompt"""
        scenes_desc = "\\n".join([
            f"Scene {i+1}: {scene.get('visuals', '')}"
            for i, scene in enumerate(script.scenes or [])
        ])
        content_type_label = self.CONTENT_TYPE_LABELS.get(script.content_type or "", script.content_type or "generic")
        style_label = self.STYLE_LABELS.get(style, style)
        platform_label = self.PLATFORM_LABELS.get(platform or "", platform or "通用平台")
        motion_guidance = self._build_motion_guidance(script.content_type or "", style)

        return f"""
Platform: {platform_label}
Content Type: {content_type_label}
Style: {style_label}
Duration: {script.duration} seconds

Script: {script.title}
Hook: {script.hook}

Scenes:
{scenes_desc}

Requirements:
- Maintain character consistency across scenes
- Smooth transitions between scenes
- Match the emotional tone of the script
- High quality, professional look
- Keep pacing and visual grammar aligned with the requested content type
- {motion_guidance}
"""

    def _build_motion_guidance(self, content_type: str, style: str) -> str:
        if content_type == "knowledge":
            return "Use clean framing, legible overlays, and stronger visual emphasis on explanation points."
        if content_type == "news":
            return "Use punchy cuts, urgent motion, and stronger headline-style scene transitions."
        if content_type == "review":
            return "Use comparison shots, detail close-ups, and clear contrast between options."
        if content_type == "story":
            return "Use cinematic framing, emotional pacing, and more expressive scene-to-scene progression."
        if content_type == "product":
            return "Use product hero shots, use-case moments, and stronger conversion-oriented visual beats."
        if style == "fast":
            return "Keep transitions brisk and visual focus changes frequent."
        return "Keep motion natural and easy to follow."
    
    async def process_task(self, task_id: str) -> VideoTask:
        """Process video generation task"""
        from sqlalchemy import select
        result = await self.session.execute(select(VideoTask).where(VideoTask.uuid == task_id))
        task = result.scalar_one_or_none()
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        task.status = "processing"
        await self.session.flush()
        
        try:
            provider_result = await self._call_seedance(task.prompt, task.duration, task.size)
            provider_video_url = provider_result["video_url"]
            video_bytes = await self._materialize_video_content(task.uuid, provider_video_url)
            stored_video_url = await self.storage.save_video(
                task_uuid=task.uuid,
                content=video_bytes,
            )
            
            task.status = "completed"
            task.progress = 1.0
            task.video_url = stored_video_url
            task.completed_at = datetime.now().isoformat()
            task.api_cost = provider_result["cost"]
            task._token_usage = provider_result["token_usage"]  # type: ignore[attr-defined]
            await self.audit_service.record_cost(
                source_type="video",
                source_uuid=task.uuid,
                provider="seedance",
                model_name=self.model,
                amount=float(task.api_cost or 0.0),
                request_summary=task.prompt[:500],
                metadata_json={
                    "script_id": task.script_id,
                    "duration": task.duration,
                    "provider_video_url": provider_video_url,
                    "storage_backend": self.storage_runtime.backend,
                    "token_usage": provider_result["token_usage"],
                },
            )
            
            logger.info("Video generation completed", uuid=task_id)
            
        except Exception as e:
            task.status = "failed"
            task.error_message = str(e)
            logger.error("Video generation failed", uuid=task_id, error=str(e))
        
        return task
    
    async def _call_seedance(self, prompt: str, duration: int, size: str) -> dict[str, object]:
        """Call Seedance API with placeholder fallback when not configured."""
        logger.info("Calling Seedance API", model=self.model, duration=duration, configured=self.client.is_configured)
        if should_use_placeholder(self.provider):
            await asyncio.sleep(0.1)
            return self._placeholder_provider_result(prompt, duration)

        try:
            response = await self.client.create_video(
                model=self.model,
                prompt=prompt,
                duration=duration,
                ratio=self._size_to_ratio(size),
            )
            resolved = self._extract_provider_video_result(response.data)
            for key in ("video_url", "url", "download_url"):
                value = resolved.get(key)
                if value:
                    return {
                        "video_url": value,
                        "cost": float(resolved.get("cost", self._estimate_cost(duration))),
                        "token_usage": response.usage.to_dict(),
                    }
            raise ValueError("Seedance response did not contain a video URL")
        except (AIProviderError, KeyError, TypeError, ValueError) as exc:
            logger.warning("Seedance call fallback to placeholder", error=str(exc))
            if should_use_placeholder(self.provider):
                await asyncio.sleep(0.1)
                return self._placeholder_provider_result(prompt, duration)
            raise

    def _placeholder_provider_result(self, prompt: str, duration: int) -> dict[str, object]:
        return {
            "video_url": "https://example.com/video_placeholder.mp4",
            "cost": self._estimate_cost(duration),
            "token_usage": self.client.normalize_usage(
                None,
                prompt=prompt,
                completion_text="video placeholder",
            ).to_dict(),
        }

    @staticmethod
    def _extract_provider_video_result(payload: dict[str, object]) -> dict[str, object]:
        if isinstance(payload.get("data"), dict):
            data = payload["data"]
            if isinstance(data, dict):
                return data
        if isinstance(payload.get("task"), dict):
            task = payload["task"]
            if isinstance(task, dict):
                return task
        return payload

    @staticmethod
    def _size_to_ratio(size: str) -> str:
        normalized = (size or "").strip()
        mapping = {
            "1080x1920": "9:16",
            "720x1280": "9:16",
            "1920x1080": "16:9",
            "1280x720": "16:9",
            "1080x1080": "1:1",
        }
        return mapping.get(normalized, "9:16")

    async def _materialize_video_content(self, task_uuid: str, provider_video_url: str) -> bytes:
        """Build or download bytes before storing into the configured backend."""
        if provider_video_url and "example.com/video_placeholder.mp4" not in provider_video_url:
            try:
                return await download_video_bytes(provider_video_url)
            except Exception as exc:
                logger.warning(
                    "Falling back to placeholder video bytes",
                    task_uuid=task_uuid,
                    error=str(exc),
                )
        return build_placeholder_video_bytes(task_uuid)
    
    def _estimate_cost(self, duration: int) -> float:
        """Estimate video generation cost"""
        # Seedance 2.0: ~.50-2.00 per second
        rate = 1.0  # $/second
        return round(duration * rate, 4)
    
    async def get_task_status(self, task_id: str) -> Optional[VideoTask]:
        """Get task status"""
        from sqlalchemy import select
        result = await self.session.execute(select(VideoTask).where(VideoTask.uuid == task_id))
        return result.scalar_one_or_none()

    async def review_task(self, task_id: str, approved: bool, feedback: str = "") -> VideoTask:
        """Review generated video task."""
        from sqlalchemy import select

        result = await self.session.execute(select(VideoTask).where(VideoTask.uuid == task_id))
        task = result.scalar_one_or_none()
        if not task:
            raise ValueError(f"Task {task_id} not found")
        if task.status not in {"completed", "approved", "rejected"}:
            raise ValueError("Video task must be completed before review")

        status_before = task.status
        task.status = "approved" if approved else "rejected"
        if approved:
            task.quality_score = 1.0
        task.quality_report = {"feedback": feedback, "reviewed_at": datetime.now().isoformat()}
        await self.audit_service.record_review(
            item_type="video",
            item_uuid=task.uuid,
            stage="video_review",
            approved=approved,
            feedback=feedback,
            status_before=status_before,
            status_after=task.status,
            review_payload={"script_id": task.script_id},
        )
        return task

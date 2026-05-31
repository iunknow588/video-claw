from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger

logger = get_logger(__name__)


class PublishService:
    """Structured publish-stage service placeholder."""

    def __init__(self, session: AsyncSession):
        self.session = session

    def execute_publish(self, payload: dict[str, Any]) -> dict[str, Any]:
        publish_plan = payload.get("publish_plan", {})
        platform_payload = payload.get("platform_payload", {})
        trace_id = payload.get("trace_id")
        video_url = publish_plan.get("video_url")
        platform = publish_plan.get("platform", "unknown")
        publish_id = f"{platform}:{str(trace_id)[:8]}" if trace_id else None
        base_result = {
            "publish_id": publish_id,
            "platform": platform,
            "trace_id": trace_id,
            "platform_payload": platform_payload,
            "publish_plan": publish_plan,
        }

        if not video_url:
            result = {**base_result, "status": "skipped", "reason": "missing_video_url"}
            logger.info("Publish skipped", platform=platform, reason="missing_video_url")
            return result

        result = {
            **base_result,
            "status": "submitted",
            "video_url": video_url,
            "adapter": "stub",
            "submission": {
                "target": platform,
                "title": publish_plan.get("title"),
                "video_task_id": publish_plan.get("video_task_id"),
                "audience": publish_plan.get("audience"),
            },
        }
        logger.info("Publish submitted", platform=platform, publish_id=publish_id)
        return result

"""
AI Analysis Service
Uses DeepSeek for content reverse engineering
"""

import json
from typing import Any, Dict

from departments.CEO.core.logging import get_logger
from departments.CIO.models.analysis import AnalysisReport
from departments.CIO.models.hotspot import HotspotItem
from departments.CIO.services.data_access.analysis_repository import AnalysisRepository
from departments.CQO.services.audit import AuditService
from departments.CTO.services.ai_clients import (
    AIProviderError,
    build_xfyun_maas_client,
    get_ai_provider_config,
    should_use_placeholder,
)

logger = get_logger(__name__)


class AIAnalysisService:
    """Service for AI-powered content analysis."""

    def __init__(self, session):
        self.provider = get_ai_provider_config("xfyun_maas")
        self.model = self.provider.model
        self.audit_service = AuditService(session)
        self.repository = AnalysisRepository(session)
        self.client = build_xfyun_maas_client(self.provider)

    async def analyze_content(self, hotspot: HotspotItem) -> AnalysisReport:
        prompt = self._build_analysis_prompt(hotspot)
        analysis_data = await self._call_text_analysis(prompt, hotspot)

        report = await self.repository.create(
            {
                "hotspot_id": hotspot.uuid,
                "analysis_type": "comprehensive",
                "content_structure": analysis_data.get("content_structure", {}),
                "emotion_curve": analysis_data.get("emotion_curve", {}),
                "hook_design": analysis_data.get("hook_design", {}),
                "framework_summary": analysis_data.get("framework_summary", ""),
                "reusable_elements": analysis_data.get("reusable_elements", []),
                "risk_warnings": analysis_data.get("risk_warnings", []),
                "api_cost": analysis_data.get("cost", 0.0),
            }
        )
        report._token_usage = analysis_data.get("token_usage", {})  # type: ignore[attr-defined]

        await self.audit_service.record_cost(
            source_type="CCO",
            source_uuid=report.uuid,
            provider=self.provider.provider,
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

    async def _call_text_analysis(self, prompt: str, hotspot: HotspotItem) -> Dict[str, Any]:
        logger.info("Calling XFYun MaaS API", model=self.model, configured=self.client.is_configured)
        if should_use_placeholder(self.provider):
            return self._placeholder_response(hotspot)

        try:
            response = await self.client.chat_json(
                model=self.model,
                prompt=prompt,
                system_prompt="You are a structured analysis assistant. Return valid JSON only.",
                temperature=0.3,
            )
            return {
                "content_structure": response.data.get("content_structure", {}),
                "emotion_curve": response.data.get("emotion_curve", {}),
                "hook_design": response.data.get("hook_design", {}),
                "framework_summary": self._normalize_framework_summary(
                    response.data.get("framework_summary", "")
                ),
                "reusable_elements": response.data.get("reusable_elements", []),
                "risk_warnings": response.data.get("risk_warnings", []),
                "cost": float(response.data.get("cost", 0.0)),
                "token_usage": response.usage.to_dict(),
            }
        except (AIProviderError, KeyError, TypeError, ValueError) as exc:
            logger.warning("XFYun MaaS call fallback to placeholder", error=str(exc))
            if should_use_placeholder(self.provider):
                return self._placeholder_response(hotspot)
            raise

    def _placeholder_response(self, hotspot: HotspotItem) -> Dict[str, Any]:
        title = str(hotspot.title or "当前热点内容").strip()
        category = str(hotspot.category or "通用内容").strip()
        return {
            "content_structure": {
                "opening": "前3秒先抛出门店经营痛点或反常识问题，快速建立停留理由。",
                "middle": "用2到3个步骤拆解解决办法，给出明确动作或判断标准。",
                "closing": "总结可执行结论，并引导收藏、咨询或继续查看。",
            },
            "emotion_curve": {
                "start": "问题感",
                "middle": "理解感",
                "end": "获得感",
            },
            "hook_design": {
                "type": "问题切入",
                "pattern": f"围绕《{title}》先讲常见误区，再给出可执行办法。",
            },
            "framework_summary": f"该内容更适合做成“痛点切入 - 步骤拆解 - 结果总结”的 {category} 短视频结构。",
            "reusable_elements": [
                "前3秒抛出痛点",
                "步骤化表达",
                "数字或案例强化说服力",
                "结尾给出行动建议",
            ],
            "risk_warnings": ["注意避免直接搬运原视频镜头、原句和封面表达。"],
            "cost": 0.05,
            "token_usage": self.client.normalize_usage(
                None,
                prompt="placeholder-analysis",
                completion_text="structured placeholder analysis",
            ).to_dict(),
        }

    def _normalize_framework_summary(self, value: Any) -> str:
        if isinstance(value, str):
            return value
        if value is None:
            return ""
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return str(value)

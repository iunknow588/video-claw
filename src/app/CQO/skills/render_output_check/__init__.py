from __future__ import annotations

from pathlib import Path
from typing import Any

from app.CEO.skills.base import BaseSkill
from app.CIO.services.storage import asset_exists


class RenderOutputCheckSkill(BaseSkill):
    skill_name = "lead.qa.render_output_check"
    description = "Checks whether the final render artifact and render manifest are present and usable."
    parameters_schema = {
        "type": "object",
        "properties": {
            "platform": {"type": "string"},
            "render_bundle": {"type": "object"},
        },
        "required": ["platform", "render_bundle"],
    }
    tags = ["lead", "qa", "render", "output"]
    retry_policy = {"max_retries": 1, "backoff": 0.0}
    dependencies = ["lead.production.render_execute"]

    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        render_bundle = input_data.get("render_bundle") or {}
        issues: list[str] = []
        score = 1.0

        delivery_asset_url = str(render_bundle.get("delivery_asset_url") or "")
        manifest_path = str(render_bundle.get("render_manifest_path") or "")
        render_mode = str(render_bundle.get("render_mode") or "unknown")
        local_render_path = str(render_bundle.get("local_render_path") or "")
        input_count = int(render_bundle.get("input_count") or 0)

        if not delivery_asset_url:
            issues.append("最终渲染产物地址缺失。")
            score -= 0.5
        elif not self._asset_exists(delivery_asset_url):
            issues.append("最终渲染产物地址不可访问或对应本地文件不存在。")
            score -= 0.35

        if not manifest_path or not Path(manifest_path).exists():
            issues.append("渲染清单未落盘。")
            score -= 0.2
        if render_mode == "ffmpeg_preview" and (not local_render_path or not Path(local_render_path).exists()):
            issues.append("标记为 ffmpeg 预览渲染，但本地渲染文件不存在。")
            score -= 0.2
        if input_count <= 0:
            issues.append("渲染输入清单为空。")
            score -= 0.15
        if render_mode == "preview_placeholder":
            score -= 0.05
            issues.append("当前为预览级占位成片，可用于联调但不是正式实拍/生成成片。")

        passed = score >= 0.75
        if passed and len(issues) == 1 and render_mode == "preview_placeholder":
            pass
        elif passed and not issues:
            issues.append("渲染产物与清单均已齐备。")

        return {
            "dimension": "render_output",
            "applicable": True,
            "pass": passed,
            "score": round(max(score, 0.0), 4),
            "issues": issues,
            "recommendation": "通过，可进入发布或交付阶段。" if passed else "建议回到制作组重新执行渲染或修复输出路径。",
        }

    def _asset_exists(self, asset_url: str) -> bool:
        return asset_exists(asset_url)

    def validate_input(self, input_data: dict[str, Any]) -> bool:
        return isinstance(input_data, dict) and "platform" in input_data and "render_bundle" in input_data

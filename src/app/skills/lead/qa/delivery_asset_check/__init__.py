from __future__ import annotations

from pathlib import Path
from typing import Any

from app.skills.base import BaseSkill


class DeliveryAssetCheckSkill(BaseSkill):
    skill_name = "lead.qa.delivery_asset_check"
    description = "Checks whether narration, subtitles, material mapping, and composition inputs are complete."
    parameters_schema = {
        "type": "object",
        "properties": {
            "script": {"type": "object"},
            "material_bundle": {"type": "object"},
            "subtitle_bundle": {"type": "object"},
            "voiceover_bundle": {"type": "object"},
            "composition_bundle": {"type": "object"},
        },
        "required": ["script"],
    }
    tags = ["lead", "qa", "delivery", "asset"]
    retry_policy = {"max_retries": 1, "backoff": 0.0}
    dependencies = [
        "lead.research.material_search",
        "lead.production.subtitle_compose",
        "lead.production.voiceover_generate",
        "lead.production.video_compose_plan",
    ]
    required_tokens = ["script"]

    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        script = input_data.get("script") or {}
        scenes = list(script.get("scenes") or [])
        material_bundle = input_data.get("material_bundle") or {}
        subtitle_bundle = input_data.get("subtitle_bundle") or {}
        voiceover_bundle = input_data.get("voiceover_bundle") or {}
        composition_bundle = input_data.get("composition_bundle") or {}

        issues: list[str] = []
        score = 1.0

        subtitle_file = subtitle_bundle.get("subtitle_file")
        audio_file = voiceover_bundle.get("audio_file")
        subtitle_items = list(subtitle_bundle.get("subtitle_items") or [])
        voice_segments = list(voiceover_bundle.get("voice_segments") or [])
        scene_material_map = list(material_bundle.get("scene_material_map") or [])
        ffmpeg_inputs = list(((composition_bundle.get("ffmpeg_plan") or {}).get("inputs") or []))
        existing_material_paths = [
            str(item.get("cache_path"))
            for item in scene_material_map
            if item.get("cache_path") and Path(str(item.get("cache_path"))).exists()
        ]

        if not subtitle_file or not Path(subtitle_file).exists():
            issues.append("字幕文件未落盘或路径无效。")
            score -= 0.3
        if not audio_file or not Path(audio_file).exists():
            issues.append("旁白音频未落盘或路径无效。")
            score -= 0.3
        if scenes and len(subtitle_items) != len(scenes):
            issues.append("字幕分段数量与脚本场景数量不一致。")
            score -= 0.15
        if scenes and len(voice_segments) != len(scenes):
            issues.append("旁白分段数量与脚本场景数量不一致。")
            score -= 0.15
        if scenes and len(scene_material_map) != len(scenes):
            issues.append("素材映射数量与脚本场景数量不一致。")
            score -= 0.1
        if scene_material_map and not existing_material_paths:
            issues.append("素材映射已生成，但本地素材缓存文件仍未物化。")
            score -= 0.1
        if subtitle_file and subtitle_file not in ffmpeg_inputs:
            issues.append("合成计划未包含字幕输入。")
            score -= 0.1
        if audio_file and audio_file not in ffmpeg_inputs:
            issues.append("合成计划未包含旁白音频输入。")
            score -= 0.1

        passed = score >= 0.75
        if passed and not issues:
            issues.append("旁白、字幕、素材映射与合成输入均已齐备。")

        return {
            "dimension": "delivery_asset",
            "applicable": True,
            "pass": passed,
            "score": round(max(score, 0.0), 4),
            "issues": issues,
            "recommendation": "通过，可进入正式交付或发布阶段。" if passed else "建议回到制作组补齐资产并重建合成计划。",
        }

    def validate_input(self, input_data: dict[str, Any]) -> bool:
        return isinstance(input_data, dict) and "script" in input_data

from __future__ import annotations

from typing import Any


class VideoCompositionService:
    """Build a portable composition plan inspired by ffmpeg/MoviePy assembly workflows."""

    PLATFORM_PRESETS = {
        "douyin": {"resolution": "1080x1920", "aspect_ratio": "9:16", "fps": 30},
        "xiaohongshu": {"resolution": "1080x1920", "aspect_ratio": "9:16", "fps": 30},
        "xigua": {"resolution": "1920x1080", "aspect_ratio": "16:9", "fps": 30},
        "bilibili": {"resolution": "1920x1080", "aspect_ratio": "16:9", "fps": 30},
    }

    def build_plan(
        self,
        *,
        platform: str,
        script: dict[str, Any],
        material_bundle: dict[str, Any] | None,
        subtitle_bundle: dict[str, Any] | None,
        voiceover_bundle: dict[str, Any] | None,
        video_task: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        preset = self.PLATFORM_PRESETS.get(platform, self.PLATFORM_PRESETS["douyin"])
        scenes = list(script.get("scenes") or [])
        scene_map = list((material_bundle or {}).get("scene_material_map") or [])
        candidates = list((material_bundle or {}).get("material_candidates") or [])
        subtitle_items = list((subtitle_bundle or {}).get("subtitle_items") or [])
        voice_segments = list((voiceover_bundle or {}).get("voice_segments") or [])

        scene_clips = []
        for index, scene in enumerate(scenes):
            mapped = scene_map[index] if index < len(scene_map) else {}
            matched_candidate = next(
                (item for item in candidates if item.get("candidate_id") == mapped.get("candidate_id")),
                None,
            )
            voice_segment = voice_segments[index] if index < len(voice_segments) else None
            subtitle_segment = subtitle_items[index] if index < len(subtitle_items) else None
            scene_clips.append(
                {
                    "scene_index": index,
                    "timing": scene.get("timing"),
                    "visuals": scene.get("visuals"),
                    "text_overlay": scene.get("text"),
                    "audio_line": scene.get("audio"),
                    "material_candidate": matched_candidate,
                    "voice_segment": voice_segment,
                    "subtitle_segment": subtitle_segment,
                    "transition": "crossfade" if index > 0 else "cut",
                }
            )

        ffmpeg_inputs = [
            item["cache_path"]
            for item in candidates
            if item.get("cache_path")
        ]
        if voiceover_bundle and voiceover_bundle.get("audio_file"):
            ffmpeg_inputs.append(str(voiceover_bundle["audio_file"]))
        if subtitle_bundle and subtitle_bundle.get("subtitle_file"):
            ffmpeg_inputs.append(str(subtitle_bundle["subtitle_file"]))

        return {
            "platform": platform,
            "render_preset": preset,
            "scene_clips": scene_clips,
            "audio_track": {
                "file": (voiceover_bundle or {}).get("audio_file"),
                "provider": (voiceover_bundle or {}).get("provider"),
                "voice_profile": (voiceover_bundle or {}).get("voice_profile"),
            },
            "subtitle_track": {
                "file": (subtitle_bundle or {}).get("subtitle_file"),
                "line_count": len(subtitle_items),
            },
            "existing_video_task": video_task,
            "ffmpeg_plan": {
                "concat_mode": "demuxer",
                "transition_mode": "crossfade",
                "filters": ["scale", "fps", "subtitles", "amix"],
                "inputs": ffmpeg_inputs,
            },
        }

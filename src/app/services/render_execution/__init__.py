from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any

from app.core.config import settings
from app.services.storage import build_placeholder_video_bytes, get_video_storage


class RenderExecutionService:
    """Turn a composition plan into a delivery-facing render artifact."""

    def __init__(self) -> None:
        self.render_root = Path(settings.MEDIA_ROOT) / "renders"
        self.storage = get_video_storage()

    async def execute(
        self,
        *,
        trace_id: str,
        platform: str,
        duration: int,
        composition_bundle: dict[str, Any],
        video_task: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        manifest_path = self._write_manifest(
            trace_id=trace_id,
            payload={
                "trace_id": trace_id,
                "platform": platform,
                "duration": duration,
                "composition_bundle": composition_bundle,
                "video_task": video_task,
            },
        )

        source_video_url = None
        render_mode = "preview_placeholder"
        render_status = "rendered"
        delivery_asset_url = None
        local_render_path = None

        if video_task and video_task.get("video_url"):
            source_video_url = str(video_task["video_url"])
            delivery_asset_url = source_video_url
            render_mode = "passthrough_video_task"
            render_status = "ready"
        else:
            preview_bytes, render_mode, local_render_path = self._build_preview_video(
                trace_id=trace_id,
                duration=duration,
                composition_bundle=composition_bundle,
            )
            delivery_asset_url = await self.storage.save_video(
                task_uuid=f"render-{trace_id}",
                content=preview_bytes,
            )

        ffmpeg_plan = composition_bundle.get("ffmpeg_plan") or {}
        return {
            "render_status": render_status,
            "render_mode": render_mode,
            "delivery_asset_url": delivery_asset_url,
            "source_video_url": source_video_url,
            "local_render_path": local_render_path,
            "render_manifest_path": str(manifest_path),
            "input_count": len(ffmpeg_plan.get("inputs") or []),
            "filter_chain": list(ffmpeg_plan.get("filters") or []),
            "scene_clip_count": len(composition_bundle.get("scene_clips") or []),
            "materialized_clip_count": len(
                [
                    clip for clip in (composition_bundle.get("scene_clips") or [])
                    if ((clip.get("material_candidate") or {}).get("cache_path"))
                    and Path(str((clip.get("material_candidate") or {}).get("cache_path"))).exists()
                ]
            ),
        }

    def _write_manifest(self, *, trace_id: str, payload: dict[str, Any]) -> Path:
        self.render_root.mkdir(parents=True, exist_ok=True)
        manifest_path = self.render_root / f"{trace_id}.json"
        manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return manifest_path

    def _build_preview_video(
        self,
        *,
        trace_id: str,
        duration: int,
        composition_bundle: dict[str, Any],
    ) -> tuple[bytes, str, str | None]:
        rendered = self._render_ffmpeg_preview(trace_id=trace_id, duration=duration, composition_bundle=composition_bundle)
        if rendered is not None:
            return rendered, "ffmpeg_preview", str((self.render_root / f"{trace_id}.mp4"))
        return build_placeholder_video_bytes(f"render-{trace_id}"), "preview_placeholder", None

    def _render_ffmpeg_preview(
        self,
        *,
        trace_id: str,
        duration: int,
        composition_bundle: dict[str, Any],
    ) -> bytes | None:
        ffmpeg_binary = shutil.which("ffmpeg")
        if not ffmpeg_binary:
            return None

        render_preset = composition_bundle.get("render_preset") or {}
        resolution = str(render_preset.get("resolution") or "1080x1920")
        fps = int(render_preset.get("fps") or 30)
        audio_track = composition_bundle.get("audio_track") or {}
        audio_file = audio_track.get("file")
        scene_clips = list(composition_bundle.get("scene_clips") or [])

        self.render_root.mkdir(parents=True, exist_ok=True)
        output_path = self.render_root / f"{trace_id}.mp4"
        base_video_path = self.render_root / f"{trace_id}.video.mp4"

        try:
            self._render_scene_video_track(
                ffmpeg_binary=ffmpeg_binary,
                output_path=base_video_path,
                resolution=resolution,
                fps=fps,
                total_duration=max(duration, 1),
                scene_clips=scene_clips,
            )
            command = [
                ffmpeg_binary,
                "-y",
                "-i",
                str(base_video_path),
            ]
            if audio_file and Path(str(audio_file)).exists():
                command.extend(["-i", str(audio_file)])
            else:
                command.extend(["-f", "lavfi", "-i", f"anullsrc=r=16000:cl=mono:d={max(duration, 1)}"])
            command.extend(
                [
                    "-shortest",
                    "-c:v",
                    "copy",
                    "-c:a",
                    "aac",
                    "-movflags",
                    "+faststart",
                    str(output_path),
                ]
            )
            self._run_ffmpeg(command)
            return output_path.read_bytes()
        except Exception:
            return None

    def _render_scene_video_track(
        self,
        *,
        ffmpeg_binary: str,
        output_path: Path,
        resolution: str,
        fps: int,
        total_duration: int,
        scene_clips: list[dict[str, Any]],
    ) -> None:
        if not scene_clips:
            command = [
                ffmpeg_binary,
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"color=c=black:s={resolution}:d={max(total_duration, 1)}:r={fps}",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                str(output_path),
            ]
            self._run_ffmpeg(command)
            return

        durations = self._scene_durations(scene_clips=scene_clips, total_duration=total_duration)
        with tempfile.TemporaryDirectory(prefix="lobster-render-scenes-") as temp_dir:
            temp_root = Path(temp_dir)
            clip_paths: list[Path] = []
            for index, scene in enumerate(scene_clips):
                clip_path = temp_root / f"scene_{index:03d}.mp4"
                clip_paths.append(clip_path)
                clip_duration = max(durations[index], 0.3)
                source_clip = self._ensure_scene_source_clip(
                    ffmpeg_binary=ffmpeg_binary,
                    scene=scene,
                    resolution=resolution,
                    fps=fps,
                    duration=clip_duration,
                    index=index,
                )
                if source_clip and source_clip.exists():
                    command = [
                        ffmpeg_binary,
                        "-y",
                        "-stream_loop",
                        "-1",
                        "-i",
                        str(source_clip),
                        "-t",
                        f"{clip_duration:.3f}",
                        "-vf",
                        f"scale={resolution},fps={fps}",
                        "-c:v",
                        "libx264",
                        "-pix_fmt",
                        "yuv420p",
                        str(clip_path),
                    ]
                else:
                    color = self._scene_color(index=index, scene=scene)
                    command = [
                        ffmpeg_binary,
                        "-y",
                        "-f",
                        "lavfi",
                        "-i",
                        f"color=c={color}:s={resolution}:d={clip_duration:.3f}:r={fps}",
                        "-c:v",
                        "libx264",
                        "-pix_fmt",
                        "yuv420p",
                        str(clip_path),
                    ]
                self._run_ffmpeg(command)

            concat_list = temp_root / "concat.txt"
            concat_list.write_text(
                "".join(f"file '{path.as_posix()}'\n" for path in clip_paths),
                encoding="utf-8",
            )
            command = [
                ffmpeg_binary,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_list),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                str(output_path),
            ]
            self._run_ffmpeg(command)

    def _scene_durations(self, *, scene_clips: list[dict[str, Any]], total_duration: int) -> list[float]:
        durations: list[float] = []
        for scene in scene_clips:
            voice_segment = scene.get("voice_segment") or {}
            start = voice_segment.get("start")
            end = voice_segment.get("end")
            if start is not None and end is not None and float(end) > float(start):
                durations.append(round(float(end) - float(start), 3))
                continue
            timing = str(scene.get("timing") or "")
            parsed = self._timing_to_duration(timing)
            if parsed is not None and parsed > 0:
                durations.append(parsed)
                continue
            durations.append(0.0)

        missing = [index for index, value in enumerate(durations) if value <= 0]
        if missing:
            remaining = max(float(total_duration) - sum(value for value in durations if value > 0), 0.0)
            fallback = remaining / max(len(missing), 1) if remaining > 0 else max(float(total_duration) / max(len(scene_clips), 1), 0.5)
            for index in missing:
                durations[index] = round(max(fallback, 0.5), 3)
        return durations

    def _timing_to_duration(self, timing: str) -> float | None:
        normalized = timing.strip().lower().replace("秒", "s")
        if not normalized:
            return None
        for delimiter in ("-", "~", "至"):
            if delimiter in normalized:
                left, right = [part.strip() for part in normalized.split(delimiter, 1)]
                try:
                    return max(self._parse_time_value(right) - self._parse_time_value(left), 0.0)
                except ValueError:
                    return None
        return None

    def _parse_time_value(self, value: str) -> float:
        if ":" in value:
            minutes, seconds = value.split(":", 1)
            return int(minutes) * 60 + float(seconds)
        return float(value.rstrip("s"))

    def _scene_color(self, *, index: int, scene: dict[str, Any]) -> str:
        palette = ("#1f2937", "#1d4ed8", "#047857", "#9a3412", "#7c3aed", "#b91c1c")
        title = str(scene.get("visuals") or scene.get("text_overlay") or "")
        offset = sum(ord(char) for char in title) % len(palette) if title else 0
        return palette[(index + offset) % len(palette)]

    def _ensure_scene_source_clip(
        self,
        *,
        ffmpeg_binary: str,
        scene: dict[str, Any],
        resolution: str,
        fps: int,
        duration: float,
        index: int,
    ) -> Path | None:
        material_candidate = scene.get("material_candidate") or {}
        cache_path_raw = material_candidate.get("cache_path")
        if not cache_path_raw:
            return None

        cache_path = Path(str(cache_path_raw))
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        if cache_path.exists():
            return cache_path

        source_duration = max(
            float(material_candidate.get("duration_hint") or 0.0),
            duration,
            1.0,
        )
        color = self._scene_color(index=index, scene=scene)
        command = [
            ffmpeg_binary,
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c={color}:s={resolution}:d={source_duration:.3f}:r={fps}",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(cache_path),
        ]
        try:
            self._run_ffmpeg(command)
            return cache_path
        except Exception:
            return None

    def _run_ffmpeg(self, command: list[str]) -> None:
        subprocess.run(
            command,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

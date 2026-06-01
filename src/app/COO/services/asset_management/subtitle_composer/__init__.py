from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.CIO.services.storage import resolve_media_path


class SubtitleComposerService:
    """Compose a basic SRT file from script scenes and timing hints."""

    def __init__(self) -> None:
        self.subtitle_root = resolve_media_path("subtitles")

    def compose(
        self,
        *,
        script: dict[str, Any],
        trace_id: str | None = None,
        target_duration: int | None = None,
    ) -> dict[str, Any]:
        scenes = list(script.get("scenes") or [])
        duration = int(target_duration or script.get("duration") or max(len(scenes) * 5, 5))
        segments = self._build_segments(scenes=scenes, duration=duration, script=script)
        subtitle_items = [
            {
                "index": idx + 1,
                "start": self._format_timestamp(segment["start"]),
                "end": self._format_timestamp(segment["end"]),
                "text": segment["text"],
            }
            for idx, segment in enumerate(segments)
        ]
        subtitle_text = self._render_srt(subtitle_items)
        subtitle_path = self._write_srt(trace_id=trace_id, subtitle_text=subtitle_text)
        return {
            "subtitle_file": str(subtitle_path),
            "subtitle_items": subtitle_items,
            "subtitle_text": subtitle_text,
        }

    def _build_segments(
        self,
        *,
        scenes: list[dict[str, Any]],
        duration: int,
        script: dict[str, Any],
    ) -> list[dict[str, Any]]:
        if scenes:
            segments = []
            fallback_window = duration / max(len(scenes), 1)
            for index, scene in enumerate(scenes):
                start, end = self._parse_timing(str(scene.get("timing") or ""))
                if start is None or end is None or end <= start:
                    start = round(index * fallback_window, 3)
                    end = round(min(duration, (index + 1) * fallback_window), 3)
                text = self._scene_text(scene)
                segments.append({"start": start, "end": end, "text": text})
            return segments

        fallback_lines = [
            str(script.get("hook") or "").strip(),
            str(script.get("title") or "").strip(),
            str(script.get("cta") or "").strip(),
        ]
        lines = [line for line in fallback_lines if line]
        if not lines:
            lines = [str(script.get("topic") or "Generated subtitle").strip()]
        window = duration / max(len(lines), 1)
        return [
            {
                "start": round(index * window, 3),
                "end": round(min(duration, (index + 1) * window), 3),
                "text": line,
            }
            for index, line in enumerate(lines)
        ]

    def _scene_text(self, scene: dict[str, Any]) -> str:
        text = str(scene.get("text") or scene.get("audio") or scene.get("visuals") or "").strip()
        return re.sub(r"\s+", " ", text) or "..."

    def _parse_timing(self, raw: str) -> tuple[float | None, float | None]:
        cleaned = raw.strip().lower().replace("秒", "s")
        if not cleaned:
            return None, None
        match = re.match(r"^\s*(\d+(?:\.\d+)?)s?\s*[-~至]\s*(\d+(?:\.\d+)?)s?\s*$", cleaned)
        if match:
            return float(match.group(1)), float(match.group(2))
        colon_match = re.match(r"^\s*(\d{1,2}):(\d{2})\s*[-~至]\s*(\d{1,2}):(\d{2})\s*$", cleaned)
        if colon_match:
            start = int(colon_match.group(1)) * 60 + int(colon_match.group(2))
            end = int(colon_match.group(3)) * 60 + int(colon_match.group(4))
            return float(start), float(end)
        return None, None

    def _render_srt(self, subtitle_items: list[dict[str, Any]]) -> str:
        blocks = []
        for item in subtitle_items:
            blocks.append(
                "\n".join(
                    [
                        str(item["index"]),
                        f"{item['start']} --> {item['end']}",
                        str(item["text"]),
                    ]
                )
            )
        return "\n\n".join(blocks).strip() + "\n"

    def _write_srt(self, *, trace_id: str | None, subtitle_text: str) -> Path:
        self.subtitle_root.mkdir(parents=True, exist_ok=True)
        file_name = f"{trace_id or uuid4().hex}.srt"
        path = self.subtitle_root / file_name
        path.write_text(subtitle_text, encoding="utf-8")
        return path

    def _format_timestamp(self, seconds: float) -> str:
        total_ms = max(0, int(round(seconds * 1000)))
        hours, remainder = divmod(total_ms, 3600_000)
        minutes, remainder = divmod(remainder, 60_000)
        secs, millis = divmod(remainder, 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

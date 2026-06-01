from __future__ import annotations

import math
import struct
import wave
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.CIO.services.storage import resolve_media_path


class VoiceoverService:
    """Lightweight narration asset generator with a placeholder WAV output."""

    def __init__(self) -> None:
        self.audio_root = resolve_media_path("audio")
        self.sample_rate = 16_000

    def generate(
        self,
        *,
        script: dict[str, Any],
        trace_id: str | None = None,
        target_duration: int | None = None,
        voice_profile: str = "narrator-neutral",
    ) -> dict[str, Any]:
        scenes = list(script.get("scenes") or [])
        total_duration = int(target_duration or script.get("duration") or max(len(scenes) * 5, 5))
        segments = self._build_segments(scenes=scenes, total_duration=total_duration, script=script)
        narration_text = " ".join(segment["text"] for segment in segments if segment["text"]).strip()
        ssml = self._build_ssml(segments=segments, voice_profile=voice_profile)
        audio_path = self._write_placeholder_audio(
            trace_id=trace_id,
            duration=max(total_duration, 1),
            segments=segments,
        )
        return {
            "audio_file": str(audio_path),
            "voice_profile": voice_profile,
            "provider": "placeholder_tts",
            "narration_text": narration_text,
            "voice_segments": segments,
            "ssml": ssml,
            "audio_format": "wav",
            "sample_rate": self.sample_rate,
        }

    def _build_segments(
        self,
        *,
        scenes: list[dict[str, Any]],
        total_duration: int,
        script: dict[str, Any],
    ) -> list[dict[str, Any]]:
        if not scenes:
            text = str(script.get("hook") or script.get("title") or script.get("topic") or "").strip() or "Generated narration"
            return [
                {
                    "scene_index": 0,
                    "start": 0.0,
                    "end": float(total_duration),
                    "text": text,
                }
            ]

        default_window = total_duration / max(len(scenes), 1)
        segments: list[dict[str, Any]] = []
        for index, scene in enumerate(scenes):
            timing = str(scene.get("timing") or "")
            start, end = self._parse_timing(timing)
            if start is None or end is None or end <= start:
                start = round(index * default_window, 3)
                end = round(min(total_duration, (index + 1) * default_window), 3)
            text = str(scene.get("audio") or scene.get("text") or scene.get("visuals") or "").strip() or "..."
            segments.append(
                {
                    "scene_index": index,
                    "start": float(start),
                    "end": float(end),
                    "text": text,
                }
            )
        return segments

    def _build_ssml(self, *, segments: list[dict[str, Any]], voice_profile: str) -> str:
        lines = "".join(
            f"<p><s>{self._escape_xml(str(segment['text']))}</s></p>"
            for segment in segments
            if str(segment["text"]).strip()
        )
        return (
            '<speak version="1.0" xml:lang="zh-CN">'
            f'<voice name="{voice_profile}">{lines}</voice>'
            "</speak>"
        )

    def _write_placeholder_audio(
        self,
        *,
        trace_id: str | None,
        duration: int,
        segments: list[dict[str, Any]],
    ) -> Path:
        self.audio_root.mkdir(parents=True, exist_ok=True)
        file_name = f"{trace_id or uuid4().hex}.wav"
        path = self.audio_root / file_name
        total_frames = max(int(duration * self.sample_rate), self.sample_rate)
        amplitude = 2800
        modulation = max(1, len(segments))

        with wave.open(str(path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            frames = bytearray()
            for index in range(total_frames):
                t = index / self.sample_rate
                envelope = 0.08 if int(t * modulation) % 2 == 0 else 0.03
                sample = int(amplitude * envelope * math.sin(2 * math.pi * 220 * t))
                frames.extend(struct.pack("<h", sample))
            wav_file.writeframes(frames)
        return path

    def _parse_timing(self, raw: str) -> tuple[float | None, float | None]:
        normalized = raw.strip().lower().replace("秒", "s")
        if not normalized:
            return None, None
        for delimiter in ("-", "~", "至"):
            if delimiter in normalized:
                left, right = [part.strip() for part in normalized.split(delimiter, 1)]
                try:
                    return self._parse_time_value(left), self._parse_time_value(right)
                except ValueError:
                    return None, None
        return None, None

    def _parse_time_value(self, value: str) -> float:
        if ":" in value:
            minutes, seconds = value.split(":", 1)
            return int(minutes) * 60 + float(seconds)
        return float(value.rstrip("s"))

    def _escape_xml(self, value: str) -> str:
        return (
            value.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )

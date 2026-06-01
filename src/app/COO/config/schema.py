from __future__ import annotations

from pydantic import BaseModel, Field


class ProductionConfig(BaseModel):
    default_resolution: str = "1080p"
    default_fps: int = Field(default=30, ge=1)
    max_video_duration: int = Field(default=300, ge=1)
    ffmpeg_preset: str = "medium"
    audio_bitrate: str = "192k"
    video_bitrate: str = "5000k"
    max_file_size: int = Field(default=524288000, ge=1)

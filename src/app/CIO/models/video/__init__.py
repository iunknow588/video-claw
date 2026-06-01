"""
Video Task Model
"""

from sqlalchemy import Column, String, Integer, Text, JSON, Numeric, ForeignKey, Index
from sqlalchemy.dialects.mysql import BIGINT

from app.CIO.models.base import BaseModel


class VideoTask(BaseModel):
    """Video generation task"""
    __tablename__ = "video_tasks"
    
    script_id = Column(String(36), ForeignKey("scripts.uuid"), nullable=False, comment="Related script ID")
    status = Column(String(20), default="pending", comment="Status")
    style = Column(String(50), comment="Video style")
    size = Column(String(20), comment="Resolution")
    duration = Column(Integer, comment="Duration in seconds")
    prompt = Column(Text, comment="Generation prompt")
    video_url = Column(String(500), comment="Video URL")
    cover_url = Column(String(500), comment="Cover URL")
    progress = Column(Numeric(5, 2), default=0, comment="Progress 0-1")
    error_message = Column(Text, comment="Error message")
    quality_score = Column(Numeric(5, 4), comment="Quality score")
    quality_report = Column(JSON, comment="Quality report")
    api_cost = Column(Numeric(10, 4), comment="API call cost")
    completed_at = Column(String(50), comment="Completion timestamp")
    
    __table_args__ = (
        Index("ix_video_tasks_script_id", "script_id"),
        Index("ix_video_tasks_status", "status"),
        Index("ix_video_tasks_created_at", "created_at"),
        {"comment": "Video generation tasks"},
    )

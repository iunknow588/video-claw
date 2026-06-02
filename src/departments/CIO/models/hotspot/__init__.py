"""
Hotspot Item Model
"""

from sqlalchemy import Column, String, Integer, Text, JSON, Index
from sqlalchemy.dialects.mysql import BIGINT

from departments.CIO.models.base import BaseModel


class HotspotItem(BaseModel):
    """Hotspot content item"""
    __tablename__ = "hotspot_items"
    
    platform = Column(String(50), nullable=False, comment="Platform name")
    content_id = Column(String(100), nullable=False, comment="Platform content ID")
    title = Column(String(500), comment="Title")
    author = Column(String(100), comment="Author")
    author_id = Column(String(100), comment="Author ID")
    url = Column(String(500), comment="URL")
    cover_image = Column(String(500), comment="Cover image URL")
    video_url = Column(String(500), comment="Video URL")
    view_count = Column(Integer, default=0, comment="View count")
    like_count = Column(Integer, default=0, comment="Like count")
    comment_count = Column(Integer, default=0, comment="Comment count")
    share_count = Column(Integer, default=0, comment="Share count")
    category = Column(String(50), comment="Content category")
    tags = Column(JSON, comment="Tags list")
    duration = Column(Integer, comment="Video duration in seconds")
    fetched_at = Column(String(50), comment="Fetch timestamp")
    
    __table_args__ = (
        Index("ix_platform_content", "platform", "content_id", unique=True),
        Index("ix_platform_fetched", "platform", "fetched_at"),
        Index("ix_category", "category"),
        {"comment": "Hotspot content items"},
    )

    @property
    def source_mode(self) -> str:
        tags = {str(item).lower() for item in (self.tags or [])}
        return "mock" if {"mvp", "mock"} & tags else "provider"

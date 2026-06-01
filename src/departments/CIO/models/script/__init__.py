"""
Script Model
"""

from sqlalchemy import Column, String, Integer, Text, JSON, Numeric, ForeignKey, Index
from sqlalchemy.dialects.mysql import BIGINT

from departments.CIO.models.base import BaseModel


class Script(BaseModel):
    """Video script"""
    __tablename__ = "scripts"
    
    analysis_id = Column(String(36), ForeignKey("analysis_reports.uuid"), nullable=False, comment="Related analysis ID")
    content_type = Column(String(50), comment="Content type")
    style = Column(String(50), comment="Style type")
    topic = Column(String(200), comment="Topic")
    title = Column(String(200), comment="Script title")
    duration = Column(Integer, comment="Total duration in seconds")
    scenes = Column(JSON, comment="Scene list")
    hook = Column(Text, comment="Hook text")
    cta = Column(Text, comment="Call to action")
    tags = Column(JSON, comment="Tags")
    version = Column(Integer, default=1, comment="Version number")
    status = Column(String(20), default="pending_review", comment="Status")
    similarity_score = Column(Numeric(5, 4), comment="Similarity score")
    api_cost = Column(Numeric(10, 4), comment="API call cost")
    created_by = Column(String(100), comment="Creator")
    
    __table_args__ = (
        Index("ix_scripts_analysis_id", "analysis_id"),
        Index("ix_scripts_status", "status"),
        Index("ix_scripts_created_at", "created_at"),
        {"comment": "Video scripts"},
    )

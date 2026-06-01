"""
Review record model.
"""

from sqlalchemy import Boolean, Column, Index, JSON, String, Text

from app.CIO.models.base import BaseModel


class ReviewRecord(BaseModel):
    """Stores script and video review actions."""

    __tablename__ = "review_records"

    item_type = Column(String(20), nullable=False, comment="script / video")
    item_uuid = Column(String(36), nullable=False, comment="Reviewed item uuid")
    stage = Column(String(30), nullable=False, comment="script_review / video_review")
    approved = Column(Boolean, nullable=False, comment="Review result")
    reviewer = Column(String(100), default="system", comment="Reviewer name")
    feedback = Column(Text, comment="Review feedback")
    status_before = Column(String(20), comment="Status before review")
    status_after = Column(String(20), comment="Status after review")
    review_payload = Column(JSON, comment="Extended review payload")

    __table_args__ = (
        Index("ix_review_item", "item_type", "item_uuid"),
        Index("ix_review_stage", "stage"),
        Index("ix_review_records_created_at", "created_at"),
        {"comment": "Review records"},
    )

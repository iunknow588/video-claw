"""
CIO information event persistence model.
"""

from sqlalchemy import Column, Index, JSON, String, Text

from app.models.base import BaseModel


class InformationEvent(BaseModel):
    """Stores CIO-owned information and observability events."""

    __tablename__ = "information_events"

    trace_id = Column(String(36), nullable=True, comment="Workflow trace ID")
    level = Column(String(20), nullable=False, default="info", comment="info / warning / error")
    message = Column(Text, nullable=False, comment="Event message")
    context = Column(JSON, comment="Additional event context")

    __table_args__ = (
        Index("ix_information_events_trace_id", "trace_id"),
        Index("ix_information_events_level", "level"),
        Index("ix_information_events_created_at", "created_at"),
        {"comment": "CIO information events"},
    )

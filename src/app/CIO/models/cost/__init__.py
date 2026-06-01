"""
Cost record model.
"""

from sqlalchemy import Column, Index, JSON, Numeric, String, Text

from app.CIO.models.base import BaseModel


class CostRecord(BaseModel):
    """Stores cost usage by stage and provider."""

    __tablename__ = "cost_records"

    source_type = Column(String(30), nullable=False, comment="analysis / script / video")
    source_uuid = Column(String(36), nullable=False, comment="Related source uuid")
    provider = Column(String(50), nullable=False, comment="Service provider")
    model_name = Column(String(100), nullable=False, comment="Model name")
    amount = Column(Numeric(10, 4), nullable=False, comment="Cost amount")
    currency = Column(String(10), default="USD", comment="Currency")
    usage_type = Column(String(30), default="api_call", comment="Usage type")
    request_summary = Column(Text, comment="Prompt or request summary")
    metadata_json = Column(JSON, comment="Extra metadata")

    __table_args__ = (
        Index("ix_cost_source", "source_type", "source_uuid"),
        Index("ix_cost_provider", "provider"),
        Index("ix_cost_records_created_at", "created_at"),
        {"comment": "Cost records"},
    )

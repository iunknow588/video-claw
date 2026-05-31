"""
CIO knowledge asset persistence model.
"""

from sqlalchemy import Column, Index, JSON, String, Text

from app.models.base import BaseModel


class KnowledgeAsset(BaseModel):
    """Stores CIO-managed knowledge-base assets."""

    __tablename__ = "knowledge_assets"

    category = Column(String(50), nullable=False, comment="Knowledge category")
    asset_key = Column(String(80), nullable=False, comment="Stable asset key")
    title = Column(String(200), nullable=False, comment="Asset title")
    summary = Column(Text, default="", comment="Asset summary")
    payload = Column(JSON, comment="Optional rich payload")

    __table_args__ = (
        Index("ix_knowledge_assets_category", "category"),
        Index("ix_knowledge_assets_asset_key", "asset_key"),
        Index("ix_knowledge_assets_created_at", "created_at"),
        {"comment": "CIO knowledge assets"},
    )

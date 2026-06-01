"""
CIO artifact persistence model.
"""

from sqlalchemy import Column, Index, JSON, String

from departments.CIO.models.base import BaseModel


class ArtifactRecord(BaseModel):
    """Stores CIO-managed workflow artifacts by trace and artifact type."""

    __tablename__ = "artifact_records"

    trace_id = Column(String(36), nullable=False, comment="Workflow trace ID")
    artifact_type = Column(String(80), nullable=False, comment="Artifact type")
    source = Column(String(80), nullable=False, default="unknown", comment="Producing leader or skill")
    payload = Column(JSON, nullable=False, comment="Artifact payload")

    __table_args__ = (
        Index("ix_artifact_records_trace_type", "trace_id", "artifact_type"),
        Index("ix_artifact_records_created_at", "created_at"),
        {"comment": "CIO artifact records"},
    )

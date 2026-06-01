"""
Leader periodic and requested report persistence model.
"""

from sqlalchemy import Column, Index, JSON, String

from app.CIO.models.base import BaseModel


class LeaderReportRecord(BaseModel):
    """Stores leader reports submitted to CEO for periodic governance and pull queries."""

    __tablename__ = "leader_reports"

    leader_name = Column(String(100), nullable=False, comment="Leader name")
    report_type = Column(String(30), nullable=False, default="periodic", comment="periodic / requested / snapshot")
    cadence = Column(String(30), nullable=False, default="manual", comment="manual / daily / weekly / on_demand")
    source = Column(String(30), nullable=False, default="leader", comment="leader / ceo_pull")
    status = Column(String(20), nullable=False, default="submitted", comment="submitted / reviewed")
    report_payload = Column(JSON, nullable=False, comment="Structured report payload")

    __table_args__ = (
        Index("ix_leader_reports_leader_name", "leader_name"),
        Index("ix_leader_reports_report_type", "report_type"),
        Index("ix_leader_reports_created_at", "created_at"),
        {"comment": "Leader reports submitted to CEO"},
    )

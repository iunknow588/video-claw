"""
Workflow step log model.
"""

from sqlalchemy import Column, Index, JSON, Integer, String, Text

from app.models.base import BaseModel


class WorkflowStepLog(BaseModel):
    """Stores step-level workflow events."""

    __tablename__ = "workflow_step_logs"

    trace_id = Column(String(36), nullable=False, comment="Trace ID")
    parent_id = Column(String(36), comment="Parent trace or step ID")
    skill_name = Column(String(100), nullable=False, comment="Skill name")
    event_type = Column(String(30), nullable=False, comment="start / finish / fail / skip")
    status = Column(String(20), nullable=False, comment="pending / running / success / failed / skipped")
    input_json = Column(JSON, comment="Input payload")
    output_json = Column(JSON, comment="Output payload")
    error_message = Column(Text, comment="Error message")
    cost = Column(Integer, default=0, comment="Cost in cent-like units")
    metadata_json = Column(JSON, comment="Extra metadata")

    __table_args__ = (
        Index("ix_step_logs_trace_id", "trace_id"),
        Index("ix_step_logs_skill", "skill_name"),
        Index("ix_step_logs_event_type", "event_type"),
        Index("ix_step_logs_created_at", "created_at"),
        {"comment": "Workflow step logs"},
    )


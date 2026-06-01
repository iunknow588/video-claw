"""
Workflow run model.
"""

from sqlalchemy import Column, Index, Integer, JSON, String, Text

from app.CIO.models.base import BaseModel


class WorkflowRun(BaseModel):
    """Stores domain-driven workflow execution records."""

    __tablename__ = "workflow_runs"

    trace_id = Column(String(36), nullable=True, comment="Workflow trace ID")
    workflow_type = Column(String(50), nullable=False, comment="domain_auto_run")
    domain = Column(String(100), nullable=False, comment="Input domain")
    platform = Column(String(50), nullable=False, comment="Target platform")
    status = Column(String(20), default="pending", comment="pending / completed / failed")
    audience = Column(String(100), comment="Audience profile")
    publish_goal = Column(String(100), comment="Publish goal")
    content_type = Column(String(50), comment="Content type")
    style = Column(String(50), comment="Script style")
    video_style = Column(String(50), comment="Video style")
    duration = Column(Integer, comment="Target duration in seconds")
    expanded_queries = Column(JSON, comment="Expanded domain query list")
    selected_hotspot_ids = Column(JSON, comment="Selected hotspot uuid list")
    prompt_package = Column(JSON, comment="Prompt package snapshot")
    analysis_ids = Column(JSON, comment="Generated analysis uuid list")
    script_id = Column(String(36), comment="Generated script uuid")
    video_task_id = Column(String(36), comment="Generated video task uuid")
    result_payload = Column(JSON, comment="Final workflow result payload")
    error_message = Column(Text, comment="Workflow failure reason")

    __table_args__ = (
        Index("ix_workflow_runs_trace_id", "trace_id"),
        Index("ix_workflow_runs_domain", "domain"),
        Index("ix_workflow_runs_platform", "platform"),
        Index("ix_workflow_runs_status", "status"),
        Index("ix_workflow_runs_created_at", "created_at"),
        {"comment": "Workflow run records"},
    )

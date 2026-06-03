"""
Workflow models.
"""
from sqlalchemy import Boolean, Column, DateTime, Index, Integer, JSON, String, Text, func

from departments.CIO.models.base import BaseModel


class WorkflowRun(BaseModel):
    """Workflow run record."""
    __tablename__ = "workflow_runs"
    
    trace_id = Column(String(36), nullable=True, comment="Workflow trace ID")
    workflow_type = Column(String(50), nullable=False, comment="domain_auto_run")
    domain = Column(String(100), nullable=False, comment="Input domain")
    platform = Column(String(50), nullable=False, comment="Target platform")
    status = Column(String(20), nullable=True, comment="pending / completed / failed")
    audience = Column(String(100), nullable=True, comment="Audience profile")
    publish_goal = Column(String(100), nullable=True, comment="Publish goal")
    content_type = Column(String(50), nullable=True, comment="Content type")
    style = Column(String(50), nullable=True, comment="Script style")
    video_style = Column(String(50), nullable=True, comment="Video style")
    duration = Column(Integer(), nullable=True, comment="Target duration in seconds")
    expanded_queries = Column(JSON(), nullable=True, comment="Expanded domain query list")
    selected_hotspot_ids = Column(JSON(), nullable=True, comment="Selected hotspot uuid list")
    prompt_package = Column(JSON(), nullable=True, comment="Prompt package snapshot")
    analysis_ids = Column(JSON(), nullable=True, comment="Generated analysis uuid list")
    script_id = Column(String(36), nullable=True, comment="Generated script uuid")
    video_task_id = Column(String(36), nullable=True, comment="Generated video task uuid")
    result_payload = Column(JSON(), nullable=True, comment="Final workflow result payload")
    error_message = Column(Text(), nullable=True, comment="Workflow failure reason")
    trigger_id = Column(String(36), nullable=True, comment="Trigger ID if triggered by scheduler")

    __table_args__ = (
        Index("ix_workflow_runs_trigger_id_created_at", "trigger_id", "created_at"),
        Index("ix_workflow_runs_trigger_id_status", "trigger_id", "status"),
    )


class WorkflowTrigger(BaseModel):
    """Scheduled workflow trigger."""

    __tablename__ = "workflow_triggers"

    name = Column(String(128), nullable=False, comment="Trigger name")
    cron = Column(String(64), nullable=False, comment="Cron expression")
    domain = Column(String(64), nullable=False, comment="Domain for workflow")
    platform = Column(String(32), nullable=False, comment="Platform for workflow")
    input_params = Column(JSON(), nullable=True, comment="Workflow input params")
    enabled = Column(Boolean, default=True, nullable=False, comment="Is trigger enabled")
    last_fired_at = Column(DateTime(timezone=True), nullable=True, comment="Last fire time")
    next_fire_at = Column(DateTime(timezone=True), nullable=True, comment="Next scheduled fire time")
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_workflow_triggers_enabled", "enabled"),
        Index("ix_workflow_triggers_next_fire_at", "next_fire_at"),
    )

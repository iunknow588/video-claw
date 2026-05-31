"""add workflow runs

Revision ID: 20260529_0002
Revises: 20260527_0001
Create Date: 2026-05-29 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260529_0002"
down_revision = "20260527_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflow_runs",
        sa.Column("trace_id", sa.String(length=36), nullable=True, comment="Workflow trace ID"),
        sa.Column("workflow_type", sa.String(length=50), nullable=False, comment="domain_auto_run"),
        sa.Column("domain", sa.String(length=100), nullable=False, comment="Input domain"),
        sa.Column("platform", sa.String(length=50), nullable=False, comment="Target platform"),
        sa.Column("status", sa.String(length=20), nullable=True, comment="pending / completed / failed"),
        sa.Column("audience", sa.String(length=100), nullable=True, comment="Audience profile"),
        sa.Column("publish_goal", sa.String(length=100), nullable=True, comment="Publish goal"),
        sa.Column("content_type", sa.String(length=50), nullable=True, comment="Content type"),
        sa.Column("style", sa.String(length=50), nullable=True, comment="Script style"),
        sa.Column("video_style", sa.String(length=50), nullable=True, comment="Video style"),
        sa.Column("duration", sa.Integer(), nullable=True, comment="Target duration in seconds"),
        sa.Column("expanded_queries", sa.JSON(), nullable=True, comment="Expanded domain query list"),
        sa.Column("selected_hotspot_ids", sa.JSON(), nullable=True, comment="Selected hotspot uuid list"),
        sa.Column("prompt_package", sa.JSON(), nullable=True, comment="Prompt package snapshot"),
        sa.Column("analysis_ids", sa.JSON(), nullable=True, comment="Generated analysis uuid list"),
        sa.Column("script_id", sa.String(length=36), nullable=True, comment="Generated script uuid"),
        sa.Column("video_task_id", sa.String(length=36), nullable=True, comment="Generated video task uuid"),
        sa.Column("result_payload", sa.JSON(), nullable=True, comment="Final workflow result payload"),
        sa.Column("error_message", sa.Text(), nullable=True, comment="Workflow failure reason"),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
        comment="Workflow run records",
    )
    op.create_index("ix_workflow_runs_trace_id", "workflow_runs", ["trace_id"], unique=False)
    op.create_index("ix_workflow_runs_created_at", "workflow_runs", ["created_at"], unique=False)
    op.create_index("ix_workflow_runs_domain", "workflow_runs", ["domain"], unique=False)
    op.create_index("ix_workflow_runs_platform", "workflow_runs", ["platform"], unique=False)
    op.create_index("ix_workflow_runs_status", "workflow_runs", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_workflow_runs_trace_id", table_name="workflow_runs")
    op.drop_index("ix_workflow_runs_status", table_name="workflow_runs")
    op.drop_index("ix_workflow_runs_platform", table_name="workflow_runs")
    op.drop_index("ix_workflow_runs_domain", table_name="workflow_runs")
    op.drop_index("ix_workflow_runs_created_at", table_name="workflow_runs")
    op.drop_table("workflow_runs")

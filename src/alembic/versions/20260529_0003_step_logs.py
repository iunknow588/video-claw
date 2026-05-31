"""add workflow step logs

Revision ID: 20260529_0003
Revises: 20260529_0002
Create Date: 2026-05-29 01:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260529_0003"
down_revision = "20260529_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflow_step_logs",
        sa.Column("trace_id", sa.String(length=36), nullable=False, comment="Trace ID"),
        sa.Column("parent_id", sa.String(length=36), nullable=True, comment="Parent trace or step ID"),
        sa.Column("skill_name", sa.String(length=100), nullable=False, comment="Skill name"),
        sa.Column("event_type", sa.String(length=30), nullable=False, comment="start / finish / fail / skip"),
        sa.Column("status", sa.String(length=20), nullable=False, comment="pending / running / success / failed / skipped"),
        sa.Column("input_json", sa.JSON(), nullable=True, comment="Input payload"),
        sa.Column("output_json", sa.JSON(), nullable=True, comment="Output payload"),
        sa.Column("error_message", sa.Text(), nullable=True, comment="Error message"),
        sa.Column("cost", sa.Integer(), nullable=True, comment="Cost in cent-like units"),
        sa.Column("metadata_json", sa.JSON(), nullable=True, comment="Extra metadata"),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
        comment="Workflow step logs",
    )
    op.create_index("ix_step_logs_created_at", "workflow_step_logs", ["created_at"], unique=False)
    op.create_index("ix_step_logs_event_type", "workflow_step_logs", ["event_type"], unique=False)
    op.create_index("ix_step_logs_skill", "workflow_step_logs", ["skill_name"], unique=False)
    op.create_index("ix_step_logs_trace_id", "workflow_step_logs", ["trace_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_step_logs_trace_id", table_name="workflow_step_logs")
    op.drop_index("ix_step_logs_skill", table_name="workflow_step_logs")
    op.drop_index("ix_step_logs_event_type", table_name="workflow_step_logs")
    op.drop_index("ix_step_logs_created_at", table_name="workflow_step_logs")
    op.drop_table("workflow_step_logs")


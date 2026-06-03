"""add trigger_id to workflow_runs and workflow_triggers

Revision ID: 20260603_add_trigger_id
Revises: 20260602_0006_system_settings
Create Date: 2026-06-03
"""

from alembic import op
import sqlalchemy as sa

revision = "20260603_add_trigger_id"
down_revision = "20260602_0006"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "workflow_runs",
        sa.Column("trigger_id", sa.String(length=36), nullable=True, comment="Trigger ID if triggered by scheduler"),
    )
    op.create_index(
        "ix_workflow_runs_trigger_id_created_at",
        "workflow_runs",
        ["trigger_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_workflow_runs_trigger_id_status",
        "workflow_runs",
        ["trigger_id", "status"],
        unique=False,
    )

    op.create_table(
        "workflow_triggers",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False, comment="Trigger name"),
        sa.Column("cron", sa.String(length=64), nullable=False, comment="Cron expression"),
        sa.Column("domain", sa.String(length=64), nullable=False, comment="Domain for workflow"),
        sa.Column("platform", sa.String(length=32), nullable=False, comment="Platform for workflow"),
        sa.Column("input_params", sa.JSON(), nullable=True, comment="Workflow input params"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true(), comment="Is trigger enabled"),
        sa.Column("last_fired_at", sa.DateTime(timezone=True), nullable=True, comment="Last fire time"),
        sa.Column("next_fire_at", sa.DateTime(timezone=True), nullable=True, comment="Next scheduled fire time"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
        comment="Workflow trigger records",
    )
    op.create_index("ix_workflow_triggers_enabled", "workflow_triggers", ["enabled"], unique=False)
    op.create_index("ix_workflow_triggers_next_fire_at", "workflow_triggers", ["next_fire_at"], unique=False)


def downgrade():
    op.drop_index("ix_workflow_triggers_next_fire_at", table_name="workflow_triggers")
    op.drop_index("ix_workflow_triggers_enabled", table_name="workflow_triggers")
    op.drop_table("workflow_triggers")
    op.drop_index("ix_workflow_runs_trigger_id_status", table_name="workflow_runs")
    op.drop_index("ix_workflow_runs_trigger_id_created_at", table_name="workflow_runs")
    op.drop_column("workflow_runs", "trigger_id")

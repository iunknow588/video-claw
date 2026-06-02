"""create system settings

Revision ID: 20260602_0006
Revises: 20260602_0005
Create Date: 2026-06-02 07:15:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260602_0006"
down_revision = "20260602_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "system_settings",
        sa.Column("setting_key", sa.String(length=120), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uuid", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("setting_key"),
        sa.UniqueConstraint("uuid"),
        comment="CIO system settings",
    )
    op.create_index("ix_system_settings_setting_key", "system_settings", ["setting_key"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_system_settings_setting_key", table_name="system_settings")
    op.drop_table("system_settings")

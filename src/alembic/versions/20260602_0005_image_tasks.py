"""add image task support

Revision ID: 20260602_0005
Revises: 20260601_0004
Create Date: 2026-06-02 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260602_0005"
down_revision = "20260601_0004"
branch_labels = None
depends_on = None

sqlite_aware_pk = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "image_tasks",
        sa.Column("script_id", sa.String(length=36), nullable=True, comment="Related script ID"),
        sa.Column("status", sa.String(length=20), nullable=True, comment="Status"),
        sa.Column("provider_name", sa.String(length=50), nullable=True, comment="Image provider name"),
        sa.Column("provider_task_id", sa.String(length=100), nullable=True, comment="Provider-side task ID"),
        sa.Column("prompt", sa.Text(), nullable=True, comment="Generation prompt"),
        sa.Column("negative_prompt", sa.Text(), nullable=True, comment="Negative prompt"),
        sa.Column("aspect_ratio", sa.String(length=20), nullable=True, comment="Aspect ratio"),
        sa.Column("resolution", sa.String(length=20), nullable=True, comment="Resolution profile"),
        sa.Column("image_count", sa.Integer(), nullable=True, comment="Requested image count"),
        sa.Column("image_urls", sa.JSON(), nullable=True, comment="Generated image URLs"),
        sa.Column("primary_image_url", sa.String(length=500), nullable=True, comment="Primary image URL"),
        sa.Column("request_payload", sa.JSON(), nullable=True, comment="Provider request payload"),
        sa.Column("result_payload", sa.JSON(), nullable=True, comment="Provider result payload"),
        sa.Column("error_message", sa.Text(), nullable=True, comment="Error message"),
        sa.Column("api_cost", sa.Numeric(precision=10, scale=4), nullable=True, comment="API call cost"),
        sa.Column("completed_at", sa.String(length=50), nullable=True, comment="Completion timestamp"),
        sa.Column("id", sqlite_aware_pk, autoincrement=True, nullable=False),
        sa.Column("uuid", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["script_id"], ["scripts.uuid"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
        comment="Image generation tasks",
    )
    op.create_index("ix_image_tasks_script_id", "image_tasks", ["script_id"], unique=False)
    op.create_index("ix_image_tasks_status", "image_tasks", ["status"], unique=False)
    op.create_index("ix_image_tasks_created_at", "image_tasks", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_image_tasks_created_at", table_name="image_tasks")
    op.drop_index("ix_image_tasks_status", table_name="image_tasks")
    op.drop_index("ix_image_tasks_script_id", table_name="image_tasks")
    op.drop_table("image_tasks")

"""initial mvp schema

Revision ID: 20260527_0001
Revises: None
Create Date: 2026-05-27 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260527_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cost_records",
        sa.Column("source_type", sa.String(length=30), nullable=False, comment="analysis / script / video"),
        sa.Column("source_uuid", sa.String(length=36), nullable=False, comment="Related source uuid"),
        sa.Column("provider", sa.String(length=50), nullable=False, comment="Service provider"),
        sa.Column("model_name", sa.String(length=100), nullable=False, comment="Model name"),
        sa.Column("amount", sa.Numeric(precision=10, scale=4), nullable=False, comment="Cost amount"),
        sa.Column("currency", sa.String(length=10), nullable=True, comment="Currency"),
        sa.Column("usage_type", sa.String(length=30), nullable=True, comment="Usage type"),
        sa.Column("request_summary", sa.Text(), nullable=True, comment="Prompt or request summary"),
        sa.Column("metadata_json", sa.JSON(), nullable=True, comment="Extra metadata"),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
        comment="Cost records",
    )
    op.create_index("ix_cost_provider", "cost_records", ["provider"], unique=False)
    op.create_index("ix_cost_records_created_at", "cost_records", ["created_at"], unique=False)
    op.create_index("ix_cost_source", "cost_records", ["source_type", "source_uuid"], unique=False)

    op.create_table(
        "hotspot_items",
        sa.Column("platform", sa.String(length=50), nullable=False, comment="Platform name"),
        sa.Column("content_id", sa.String(length=100), nullable=False, comment="Platform content ID"),
        sa.Column("title", sa.String(length=500), nullable=True, comment="Title"),
        sa.Column("author", sa.String(length=100), nullable=True, comment="Author"),
        sa.Column("author_id", sa.String(length=100), nullable=True, comment="Author ID"),
        sa.Column("url", sa.String(length=500), nullable=True, comment="URL"),
        sa.Column("cover_image", sa.String(length=500), nullable=True, comment="Cover image URL"),
        sa.Column("video_url", sa.String(length=500), nullable=True, comment="Video URL"),
        sa.Column("view_count", sa.Integer(), nullable=True, comment="View count"),
        sa.Column("like_count", sa.Integer(), nullable=True, comment="Like count"),
        sa.Column("comment_count", sa.Integer(), nullable=True, comment="Comment count"),
        sa.Column("share_count", sa.Integer(), nullable=True, comment="Share count"),
        sa.Column("category", sa.String(length=50), nullable=True, comment="Content category"),
        sa.Column("tags", sa.JSON(), nullable=True, comment="Tags list"),
        sa.Column("duration", sa.Integer(), nullable=True, comment="Video duration in seconds"),
        sa.Column("fetched_at", sa.String(length=50), nullable=True, comment="Fetch timestamp"),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
        comment="Hotspot content items",
    )
    op.create_index("ix_category", "hotspot_items", ["category"], unique=False)
    op.create_index("ix_platform_content", "hotspot_items", ["platform", "content_id"], unique=True)
    op.create_index("ix_platform_fetched", "hotspot_items", ["platform", "fetched_at"], unique=False)

    op.create_table(
        "review_records",
        sa.Column("item_type", sa.String(length=20), nullable=False, comment="script / video"),
        sa.Column("item_uuid", sa.String(length=36), nullable=False, comment="Reviewed item uuid"),
        sa.Column("stage", sa.String(length=30), nullable=False, comment="script_review / video_review"),
        sa.Column("approved", sa.Boolean(), nullable=False, comment="Review result"),
        sa.Column("reviewer", sa.String(length=100), nullable=True, comment="Reviewer name"),
        sa.Column("feedback", sa.Text(), nullable=True, comment="Review feedback"),
        sa.Column("status_before", sa.String(length=20), nullable=True, comment="Status before review"),
        sa.Column("status_after", sa.String(length=20), nullable=True, comment="Status after review"),
        sa.Column("review_payload", sa.JSON(), nullable=True, comment="Extended review payload"),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
        comment="Review records",
    )
    op.create_index("ix_review_item", "review_records", ["item_type", "item_uuid"], unique=False)
    op.create_index("ix_review_records_created_at", "review_records", ["created_at"], unique=False)
    op.create_index("ix_review_stage", "review_records", ["stage"], unique=False)

    op.create_table(
        "analysis_reports",
        sa.Column("hotspot_id", sa.String(length=36), nullable=False, comment="Related hotspot ID"),
        sa.Column("analysis_type", sa.String(length=20), nullable=True, comment="Analysis type"),
        sa.Column("content_structure", sa.JSON(), nullable=True, comment="Content structure"),
        sa.Column("emotion_curve", sa.JSON(), nullable=True, comment="Emotion curve"),
        sa.Column("hook_design", sa.JSON(), nullable=True, comment="Hook design"),
        sa.Column("framework_summary", sa.Text(), nullable=True, comment="Framework summary"),
        sa.Column("reusable_elements", sa.JSON(), nullable=True, comment="Reusable elements"),
        sa.Column("risk_warnings", sa.JSON(), nullable=True, comment="Risk warnings"),
        sa.Column("api_cost", sa.Numeric(precision=10, scale=4), nullable=True, comment="API call cost"),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["hotspot_id"], ["hotspot_items.uuid"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
        comment="AI analysis reports",
    )
    op.create_index("ix_analysis_reports_created_at", "analysis_reports", ["created_at"], unique=False)
    op.create_index("ix_analysis_reports_hotspot_id", "analysis_reports", ["hotspot_id"], unique=False)

    op.create_table(
        "scripts",
        sa.Column("analysis_id", sa.String(length=36), nullable=False, comment="Related analysis ID"),
        sa.Column("content_type", sa.String(length=50), nullable=True, comment="Content type"),
        sa.Column("style", sa.String(length=50), nullable=True, comment="Style type"),
        sa.Column("topic", sa.String(length=200), nullable=True, comment="Topic"),
        sa.Column("title", sa.String(length=200), nullable=True, comment="Script title"),
        sa.Column("duration", sa.Integer(), nullable=True, comment="Total duration in seconds"),
        sa.Column("scenes", sa.JSON(), nullable=True, comment="Scene list"),
        sa.Column("hook", sa.Text(), nullable=True, comment="Hook text"),
        sa.Column("cta", sa.Text(), nullable=True, comment="Call to action"),
        sa.Column("tags", sa.JSON(), nullable=True, comment="Tags"),
        sa.Column("version", sa.Integer(), nullable=True, comment="Version number"),
        sa.Column("status", sa.String(length=20), nullable=True, comment="Status"),
        sa.Column("similarity_score", sa.Numeric(precision=5, scale=4), nullable=True, comment="Similarity score"),
        sa.Column("api_cost", sa.Numeric(precision=10, scale=4), nullable=True, comment="API call cost"),
        sa.Column("created_by", sa.String(length=100), nullable=True, comment="Creator"),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["analysis_id"], ["analysis_reports.uuid"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
        comment="Video scripts",
    )
    op.create_index("ix_scripts_analysis_id", "scripts", ["analysis_id"], unique=False)
    op.create_index("ix_scripts_created_at", "scripts", ["created_at"], unique=False)
    op.create_index("ix_scripts_status", "scripts", ["status"], unique=False)

    op.create_table(
        "video_tasks",
        sa.Column("script_id", sa.String(length=36), nullable=False, comment="Related script ID"),
        sa.Column("status", sa.String(length=20), nullable=True, comment="Status"),
        sa.Column("style", sa.String(length=50), nullable=True, comment="Video style"),
        sa.Column("size", sa.String(length=20), nullable=True, comment="Resolution"),
        sa.Column("duration", sa.Integer(), nullable=True, comment="Duration in seconds"),
        sa.Column("prompt", sa.Text(), nullable=True, comment="Generation prompt"),
        sa.Column("video_url", sa.String(length=500), nullable=True, comment="Video URL"),
        sa.Column("cover_url", sa.String(length=500), nullable=True, comment="Cover URL"),
        sa.Column("progress", sa.Numeric(precision=5, scale=2), nullable=True, comment="Progress 0-1"),
        sa.Column("error_message", sa.Text(), nullable=True, comment="Error message"),
        sa.Column("quality_score", sa.Numeric(precision=5, scale=4), nullable=True, comment="Quality score"),
        sa.Column("quality_report", sa.JSON(), nullable=True, comment="Quality report"),
        sa.Column("api_cost", sa.Numeric(precision=10, scale=4), nullable=True, comment="API call cost"),
        sa.Column("completed_at", sa.String(length=50), nullable=True, comment="Completion timestamp"),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["script_id"], ["scripts.uuid"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
        comment="Video generation tasks",
    )
    op.create_index("ix_video_tasks_created_at", "video_tasks", ["created_at"], unique=False)
    op.create_index("ix_video_tasks_script_id", "video_tasks", ["script_id"], unique=False)
    op.create_index("ix_video_tasks_status", "video_tasks", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_video_tasks_status", table_name="video_tasks")
    op.drop_index("ix_video_tasks_script_id", table_name="video_tasks")
    op.drop_index("ix_video_tasks_created_at", table_name="video_tasks")
    op.drop_table("video_tasks")

    op.drop_index("ix_scripts_status", table_name="scripts")
    op.drop_index("ix_scripts_created_at", table_name="scripts")
    op.drop_index("ix_scripts_analysis_id", table_name="scripts")
    op.drop_table("scripts")

    op.drop_index("ix_analysis_reports_hotspot_id", table_name="analysis_reports")
    op.drop_index("ix_analysis_reports_created_at", table_name="analysis_reports")
    op.drop_table("analysis_reports")

    op.drop_index("ix_review_stage", table_name="review_records")
    op.drop_index("ix_review_records_created_at", table_name="review_records")
    op.drop_index("ix_review_item", table_name="review_records")
    op.drop_table("review_records")

    op.drop_index("ix_platform_fetched", table_name="hotspot_items")
    op.drop_index("ix_platform_content", table_name="hotspot_items")
    op.drop_index("ix_category", table_name="hotspot_items")
    op.drop_table("hotspot_items")

    op.drop_index("ix_cost_source", table_name="cost_records")
    op.drop_index("ix_cost_records_created_at", table_name="cost_records")
    op.drop_index("ix_cost_provider", table_name="cost_records")
    op.drop_table("cost_records")

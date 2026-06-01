"""add governance and content support tables

Revision ID: 20260601_0004
Revises: 20260529_0003
Create Date: 2026-06-01 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260601_0004"
down_revision = "20260529_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "artifact_records",
        sa.Column("trace_id", sa.String(length=36), nullable=False, comment="Workflow trace ID"),
        sa.Column("artifact_type", sa.String(length=80), nullable=False, comment="Artifact type"),
        sa.Column("source", sa.String(length=80), nullable=False, comment="Producing leader or skill"),
        sa.Column("payload", sa.JSON(), nullable=False, comment="Artifact payload"),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
        comment="CIO artifact records",
    )
    op.create_index("ix_artifact_records_trace_type", "artifact_records", ["trace_id", "artifact_type"], unique=False)
    op.create_index("ix_artifact_records_created_at", "artifact_records", ["created_at"], unique=False)

    op.create_table(
        "information_events",
        sa.Column("trace_id", sa.String(length=36), nullable=True, comment="Workflow trace ID"),
        sa.Column("level", sa.String(length=20), nullable=False, comment="info / warning / error"),
        sa.Column("message", sa.Text(), nullable=False, comment="Event message"),
        sa.Column("context", sa.JSON(), nullable=True, comment="Additional event context"),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
        comment="CIO information events",
    )
    op.create_index("ix_information_events_trace_id", "information_events", ["trace_id"], unique=False)
    op.create_index("ix_information_events_level", "information_events", ["level"], unique=False)
    op.create_index("ix_information_events_created_at", "information_events", ["created_at"], unique=False)

    op.create_table(
        "knowledge_assets",
        sa.Column("category", sa.String(length=50), nullable=False, comment="Knowledge category"),
        sa.Column("asset_key", sa.String(length=80), nullable=False, comment="Stable asset key"),
        sa.Column("title", sa.String(length=200), nullable=False, comment="Asset title"),
        sa.Column("summary", sa.Text(), nullable=True, comment="Asset summary"),
        sa.Column("payload", sa.JSON(), nullable=True, comment="Optional rich payload"),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
        comment="CIO knowledge assets",
    )
    op.create_index("ix_knowledge_assets_category", "knowledge_assets", ["category"], unique=False)
    op.create_index("ix_knowledge_assets_asset_key", "knowledge_assets", ["asset_key"], unique=False)
    op.create_index("ix_knowledge_assets_created_at", "knowledge_assets", ["created_at"], unique=False)

    op.create_table(
        "leader_reports",
        sa.Column("leader_name", sa.String(length=100), nullable=False, comment="Leader name"),
        sa.Column("report_type", sa.String(length=30), nullable=False, comment="periodic / requested / snapshot"),
        sa.Column("cadence", sa.String(length=30), nullable=False, comment="manual / daily / weekly / on_demand"),
        sa.Column("source", sa.String(length=30), nullable=False, comment="leader / ceo_pull"),
        sa.Column("status", sa.String(length=20), nullable=False, comment="submitted / reviewed"),
        sa.Column("report_payload", sa.JSON(), nullable=False, comment="Structured report payload"),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
        comment="Leader reports submitted to CEO",
    )
    op.create_index("ix_leader_reports_leader_name", "leader_reports", ["leader_name"], unique=False)
    op.create_index("ix_leader_reports_report_type", "leader_reports", ["report_type"], unique=False)
    op.create_index("ix_leader_reports_created_at", "leader_reports", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_leader_reports_created_at", table_name="leader_reports")
    op.drop_index("ix_leader_reports_report_type", table_name="leader_reports")
    op.drop_index("ix_leader_reports_leader_name", table_name="leader_reports")
    op.drop_table("leader_reports")

    op.drop_index("ix_knowledge_assets_created_at", table_name="knowledge_assets")
    op.drop_index("ix_knowledge_assets_asset_key", table_name="knowledge_assets")
    op.drop_index("ix_knowledge_assets_category", table_name="knowledge_assets")
    op.drop_table("knowledge_assets")

    op.drop_index("ix_information_events_created_at", table_name="information_events")
    op.drop_index("ix_information_events_level", table_name="information_events")
    op.drop_index("ix_information_events_trace_id", table_name="information_events")
    op.drop_table("information_events")

    op.drop_index("ix_artifact_records_created_at", table_name="artifact_records")
    op.drop_index("ix_artifact_records_trace_type", table_name="artifact_records")
    op.drop_table("artifact_records")

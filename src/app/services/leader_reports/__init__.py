from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.leader_report import LeaderReportRecord


class LeaderReportService:
    """Persists and queries leader reports submitted to the CEO governance surface."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_report(
        self,
        *,
        leader_name: str,
        report_type: str,
        cadence: str,
        source: str,
        status: str = "submitted",
        report_payload: dict[str, Any],
    ) -> LeaderReportRecord:
        record = LeaderReportRecord(
            leader_name=leader_name,
            report_type=report_type,
            cadence=cadence,
            source=source,
            status=status,
            report_payload=jsonable_encoder(report_payload),
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def list_reports(
        self,
        *,
        leader_name: str | None = None,
        report_type: str | None = None,
        limit: int = 20,
    ) -> list[LeaderReportRecord]:
        query = select(LeaderReportRecord).order_by(LeaderReportRecord.created_at.desc()).limit(limit)
        if leader_name:
            query = query.where(LeaderReportRecord.leader_name == leader_name)
        if report_type:
            query = query.where(LeaderReportRecord.report_type == report_type)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_latest_report(
        self,
        *,
        leader_name: str,
        report_type: str | None = None,
    ) -> LeaderReportRecord | None:
        query = (
            select(LeaderReportRecord)
            .where(LeaderReportRecord.leader_name == leader_name)
            .order_by(LeaderReportRecord.created_at.desc(), LeaderReportRecord.id.desc())
            .limit(1)
        )
        if report_type:
            query = query.where(LeaderReportRecord.report_type == report_type)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_latest_created_at(
        self,
        *,
        leader_name: str,
        report_type: str = "periodic",
    ) -> datetime | None:
        report = await self.get_latest_report(leader_name=leader_name, report_type=report_type)
        return report.created_at if report else None

    def serialize_report(self, record: LeaderReportRecord) -> dict[str, Any]:
        return {
            "uuid": record.uuid,
            "leader_name": record.leader_name,
            "report_type": record.report_type,
            "cadence": record.cadence,
            "source": record.source,
            "status": record.status,
            "report_payload": dict(record.report_payload or {}),
            "created_at": record.created_at,
            "updated_at": record.updated_at,
        }

"""
Audit-related services for review and cost records.
"""

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.CIO.models.cost import CostRecord
from app.CIO.models.review import ReviewRecord


class AuditService:
    """Service for persisting review and cost audit data."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def record_review(
        self,
        *,
        item_type: str,
        item_uuid: str,
        stage: str,
        approved: bool,
        reviewer: str = "system",
        feedback: str = "",
        status_before: Optional[str] = None,
        status_after: Optional[str] = None,
        review_payload: Optional[dict[str, Any]] = None,
    ) -> ReviewRecord:
        record = ReviewRecord(
            item_type=item_type,
            item_uuid=item_uuid,
            stage=stage,
            approved=approved,
            reviewer=reviewer,
            feedback=feedback,
            status_before=status_before,
            status_after=status_after,
            review_payload=review_payload or {},
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def record_cost(
        self,
        *,
        source_type: str,
        source_uuid: str,
        provider: str,
        model_name: str,
        amount: float,
        currency: str = "USD",
        usage_type: str = "api_call",
        request_summary: str = "",
        metadata_json: Optional[dict[str, Any]] = None,
    ) -> CostRecord:
        record = CostRecord(
            source_type=source_type,
            source_uuid=source_uuid,
            provider=provider,
            model_name=model_name,
            amount=amount,
            currency=currency,
            usage_type=usage_type,
            request_summary=request_summary,
            metadata_json=metadata_json or {},
        )
        self.session.add(record)
        await self.session.flush()
        return record

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.CIO.models.cost import CostRecord
from app.CFO.services.finance_runtime import get_finance_runtime
from app.CIO.services.operations import OperationsService


class FinanceService:
    """Lightweight finance summary service for CFO gatekeeping and status reporting."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.operations_service = OperationsService(session)
        self.runtime = get_finance_runtime()

    async def build_summary(self) -> dict[str, float | int | str]:
        operations_summary = await self.operations_service.build_summary()
        actual_spend = round(float((operations_summary.get("cost_breakdown") or {}).get("total", 0.0) or 0.0), 4)
        reserved_cost = await self._sum_reserved_cost()
        committed_budget = max(actual_spend, reserved_cost)
        transaction_count = await self._count_transactions()
        remaining_budget = round(
            max(self.runtime.daily_budget - committed_budget, 0.0),
            4,
        )

        return {
            "daily_budget": self.runtime.daily_budget,
            "actual_spend": actual_spend,
            "reserved_cost": reserved_cost,
            "remaining_budget": remaining_budget,
            "transaction_count": transaction_count,
            "currency": "USD",
            "alert_level": self.runtime.alert_level(committed_budget),
        }

    async def _sum_reserved_cost(self) -> float:
        result = await self.session.execute(
            select(func.sum(CostRecord.amount)).where(CostRecord.source_type == "finance")
        )
        return round(float(result.scalar_one() or 0.0), 4)

    async def _count_transactions(self) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(CostRecord).where(CostRecord.source_type == "finance")
        )
        return int(result.scalar_one() or 0)

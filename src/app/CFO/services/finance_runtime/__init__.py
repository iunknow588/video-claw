from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.CEO.core.config import settings
from app.CFO.config.schema import FinanceConfig


FinanceAlertLevel = Literal["normal", "warning", "alert", "critical"]


@dataclass(slots=True)
class FinanceRuntime:
    daily_budget: float
    warning_threshold: float
    alert_threshold: float
    critical_threshold: float

    def usage_ratio(self, amount: float) -> float:
        if self.daily_budget <= 0:
            return 0.0
        return round(max(float(amount), 0.0) / self.daily_budget, 4)

    def alert_level(self, amount: float) -> FinanceAlertLevel:
        ratio = self.usage_ratio(amount)
        if ratio >= self.critical_threshold:
            return "critical"
        if ratio >= self.alert_threshold:
            return "alert"
        if ratio >= self.warning_threshold:
            return "warning"
        return "normal"


def get_finance_runtime() -> FinanceRuntime:
    finance: FinanceConfig = settings.finance
    return FinanceRuntime(
        daily_budget=round(float(finance.daily_budget or 0.0), 4),
        warning_threshold=round(float(finance.warning_threshold or 0.0), 4),
        alert_threshold=round(float(finance.alert_threshold or 0.0), 4),
        critical_threshold=round(float(finance.critical_threshold or 0.0), 4),
    )

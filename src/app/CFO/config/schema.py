from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class FinanceConfig(BaseModel):
    daily_budget: float = Field(default=1000.0, gt=0)
    warning_threshold: float = Field(default=0.8, ge=0)
    alert_threshold: float = Field(default=1.0, ge=0)
    critical_threshold: float = Field(default=1.2, ge=0)
    api_pricing: dict[str, dict[str, float]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_thresholds(self):
        if not (self.warning_threshold <= self.alert_threshold <= self.critical_threshold):
            raise ValueError("cost thresholds must satisfy warning <= alert <= critical")
        return self

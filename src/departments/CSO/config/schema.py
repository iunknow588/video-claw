from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class HotspotLimitsConfig(BaseModel):
    default: int = Field(default=10, ge=1)
    max: int = Field(default=50, ge=1)

    @model_validator(mode="after")
    def validate_limits(self):
        if self.max < self.default:
            raise ValueError("max hotspot limit must be greater than or equal to default")
        return self


class HotspotFiltersConfig(BaseModel):
    min_view_count: int = Field(default=10000, ge=0)
    min_like_count: int = Field(default=1000, ge=0)


class HotspotConfig(BaseModel):
    schedule: list[str] = Field(default_factory=list)
    platforms: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    limits: HotspotLimitsConfig = Field(default_factory=HotspotLimitsConfig)
    filters: HotspotFiltersConfig = Field(default_factory=HotspotFiltersConfig)
    retention_days: int = Field(default=30, ge=1)

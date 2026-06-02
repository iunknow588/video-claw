from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, Field


class IdentityProfileResponse(BaseModel):
    key: str
    code: str
    name: str
    default_name: str


class IdentitySettingsResponse(BaseModel):
    names: Dict[str, str]
    profiles: List[IdentityProfileResponse]


class IdentitySettingsUpdateRequest(BaseModel):
    names: Dict[str, str] = Field(default_factory=dict)

from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, Field


class IdentityProfileResponse(BaseModel):
    key: str
    code: str
    name: str
    default_name: str


class IdentitySettingsResponse(BaseModel):
    console_title: str
    console_title_default: str
    names: Dict[str, str]
    profiles: List[IdentityProfileResponse]


class IdentitySettingsUpdateRequest(BaseModel):
    console_title: str | None = None
    names: Dict[str, str] = Field(default_factory=dict)


class CEORuntimeSettingsResponse(BaseModel):
    evolution_enabled: bool
    dispatch_mode: str
    dispatch_mode_options: List[str]
    qa_rework_max_attempts: int
    qa_reroute_strategy: str
    qa_reroute_strategy_options: List[str]
    qa_reroute_mapping: Dict[str, str]


class CEORuntimeSettingsUpdateRequest(BaseModel):
    evolution_enabled: bool | None = None
    dispatch_mode: str | None = None
    qa_rework_max_attempts: int | None = Field(default=None, ge=0)
    qa_reroute_strategy: str | None = None


class AIProviderProfileSettings(BaseModel):
    api_key: str = ""
    base_url: str = ""
    model: str = ""
    resource_id: str = ""
    configured: bool = False


class AIProviderProfileUpdateRequest(BaseModel):
    api_key: str = ""
    base_url: str = ""
    model: str = ""
    resource_id: str = ""


class HiDreamProviderSettings(BaseModel):
    app_id: str = ""
    api_key: str = ""
    api_secret: str = ""
    create_url: str = ""
    query_url: str = ""
    configured: bool = False


class HiDreamProviderUpdateRequest(BaseModel):
    app_id: str = ""
    api_key: str = ""
    api_secret: str = ""
    create_url: str = ""
    query_url: str = ""


class AIRuntimeSettings(BaseModel):
    http_timeout: float = Field(default=60.0, gt=0)
    max_retries: int = Field(default=2, ge=0)
    use_placeholder_when_unconfigured: bool = True


class APIProviderSettingsResponse(BaseModel):
    deepseek: AIProviderProfileSettings
    glm: AIProviderProfileSettings
    xfyun_maas: AIProviderProfileSettings
    hidream: HiDreamProviderSettings
    seedance: AIProviderProfileSettings
    runtime: AIRuntimeSettings


class APIProviderSettingsUpdateRequest(BaseModel):
    deepseek: AIProviderProfileUpdateRequest
    glm: AIProviderProfileUpdateRequest
    xfyun_maas: AIProviderProfileUpdateRequest
    hidream: HiDreamProviderUpdateRequest
    seedance: AIProviderProfileUpdateRequest
    runtime: AIRuntimeSettings


class SystemSettingsBundleResponse(BaseModel):
    identity: IdentitySettingsResponse
    ceo_runtime: CEORuntimeSettingsResponse
    api_providers: APIProviderSettingsResponse

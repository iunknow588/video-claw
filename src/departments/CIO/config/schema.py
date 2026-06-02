from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class DatabaseConfig(BaseModel):
    url: str
    pool_size: int = Field(default=10, ge=1)
    max_overflow: int = Field(default=20, ge=0)
    pool_timeout: int = Field(default=30, ge=1)
    echo: bool = False

    @model_validator(mode="after")
    def validate_url(self):
        if not self.url.strip():
            raise ValueError("database url cannot be empty")
        return self


class RedisConfig(BaseModel):
    host: str = "localhost"
    port: int = Field(default=6379, ge=1, le=65535)
    db: int = Field(default=0, ge=0)
    password: str | None = None
    decode_responses: bool = True

    def build_url(self) -> str:
        password_part = f":{self.password}@" if self.password else ""
        return f"redis://{password_part}{self.host}:{self.port}/{self.db}"


class AIProviderProfile(BaseModel):
    api_key: str = ""
    base_url: str
    model: str
    resource_id: str = ""


class AIRuntimeConfig(BaseModel):
    http_timeout: float = Field(default=60.0, gt=0)
    max_retries: int = Field(default=2, ge=0)
    use_placeholder_when_unconfigured: bool = True


class HiDreamProviderConfig(BaseModel):
    app_id: str = ""
    api_key: str = ""
    api_secret: str = ""
    create_url: str = ""
    query_url: str = ""
    default_resolution: str = "2k"
    default_aspect_ratio: str = "9:16"


class AIProvidersConfig(BaseModel):
    deepseek: AIProviderProfile
    glm: AIProviderProfile
    xfyun_maas: AIProviderProfile
    hidream: HiDreamProviderConfig
    seedance: AIProviderProfile
    runtime: AIRuntimeConfig


class GitHubStorageConfig(BaseModel):
    owner: str = ""
    repo: str = ""
    token: str = ""
    release_tag: str = "video-assets"


class IPFSStorageConfig(BaseModel):
    api_url: str = "http://127.0.0.1:5001"
    gateway_url: str = "https://ipfs.io/ipfs"
    pin_on_add: bool = True


class S3CompatibleStorageConfig(BaseModel):
    endpoint_url: str = ""
    access_key_id: str = ""
    secret_access_key: str = ""
    bucket: str = ""
    region: str = ""
    object_prefix: str = "videos"
    public_base_url: str = ""


class StorageConfig(BaseModel):
    video_backend: Literal["local", "github_release", "ipfs", "s3_compatible"] = "local"
    media_root: str = "runtime/media"
    media_url_prefix: str = "/media"
    media_base_url: str | None = None
    github: GitHubStorageConfig = Field(default_factory=GitHubStorageConfig)
    ipfs: IPFSStorageConfig = Field(default_factory=IPFSStorageConfig)
    s3_compatible: S3CompatibleStorageConfig = Field(default_factory=S3CompatibleStorageConfig)

    @model_validator(mode="after")
    def validate_backend_dependencies(self):
        if self.video_backend == "github_release":
            if not (self.github.owner and self.github.repo and self.github.token):
                raise ValueError("github_release backend requires owner, repo, and token")
        if self.video_backend == "s3_compatible":
            if not (
                self.s3_compatible.bucket
                and self.s3_compatible.access_key_id
                and self.s3_compatible.secret_access_key
            ):
                raise ValueError("s3_compatible backend requires bucket and access credentials")
        return self

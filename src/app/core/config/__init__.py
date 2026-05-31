"""
Application Configuration
Uses pydantic-settings for environment-based config
"""

from functools import lru_cache
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # App
    APP_NAME: str = "AI Video Auto Production Line"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, alias="DEBUG")
    ENV: str = "development"
    
    # Server
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000
    SERVER_WORKERS: int = 1
    
    # Database
    DATABASE_URL: str = Field(
        default="mysql+aiomysql://user:password@localhost:3306/ai_video_prod?charset=utf8mb4",
        alias="DATABASE_URL",
    )
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_ECHO: bool = False
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    
    # API Keys
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-v4"
    
    GLM_API_KEY: str = ""
    GLM_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4"
    GLM_MODEL: str = "glm-5.1"
    
    SEEDANCE_API_KEY: str = ""
    SEEDANCE_BASE_URL: str = "https://api.seedance.ai/v1"
    SEEDANCE_MODEL: str = "seedance-2.0"
    AI_HTTP_TIMEOUT: float = 60.0
    AI_MAX_RETRIES: int = 2
    AI_USE_PLACEHOLDER_WHEN_UNCONFIGURED: bool = True

    # Media Storage
    VIDEO_STORAGE_BACKEND: str = "local"
    MEDIA_ROOT: str = "media"
    MEDIA_URL_PREFIX: str = "/media"
    MEDIA_BASE_URL: Optional[str] = None

    GITHUB_STORAGE_OWNER: str = ""
    GITHUB_STORAGE_REPO: str = ""
    GITHUB_STORAGE_TOKEN: str = ""
    GITHUB_STORAGE_RELEASE_TAG: str = "video-assets"

    IPFS_API_URL: str = "http://127.0.0.1:5001"
    IPFS_GATEWAY_URL: str = "https://ipfs.io/ipfs"
    IPFS_PIN_ON_ADD: bool = True

    S3_ENDPOINT_URL: str = ""
    S3_ACCESS_KEY_ID: str = ""
    S3_SECRET_ACCESS_KEY: str = ""
    S3_BUCKET: str = ""
    S3_REGION: str = ""
    S3_OBJECT_PREFIX: str = "videos"
    S3_PUBLIC_BASE_URL: str = ""
    
    # Cost Control
    DAILY_BUDGET: float = 1000.0
    COST_WARNING_THRESHOLD: float = 0.8
    COST_ALERT_THRESHOLD: float = 1.0
    COST_CRITICAL_THRESHOLD: float = 1.2
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOG_FILE: str = "logs/app.log"
    
    # Monitoring
    PROMETHEUS_ENABLED: bool = True
    METRICS_PORT: int = 9090


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()

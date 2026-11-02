from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. Values come from environment variables (prefix HB_).

    Secrets are injected by the secret manager in production, never committed.
    """

    model_config = SettingsConfigDict(env_prefix="HB_", env_file=".env", extra="ignore")

    env: Literal["local", "test", "staging", "production"] = "local"
    service_name: str = "handball-api"
    log_level: str = "INFO"
    log_json: bool = True

    database_url: str = "postgresql+asyncpg://handball:handball@localhost:5432/handball"
    redis_url: str = "redis://localhost:6379/0"

    s3_endpoint_url: str | None = "http://localhost:9000"
    s3_region: str = "eu-central-2"
    s3_access_key: str = "handball"
    s3_secret_key: SecretStr = SecretStr("handball-secret")
    s3_bucket_videos: str = "videos"
    s3_bucket_artifacts: str = "artifacts"

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    sentry_dsn: SecretStr | None = None
    readiness_timeout_s: float = 2.0


@lru_cache
def get_settings() -> Settings:
    return Settings()

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class JobSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HB_", extra="ignore")

    redis_url: str = "redis://localhost:6379/0"
    api_internal_url: str = "http://localhost:8000"
    internal_token: str = "dev-only-internal-token"  # noqa: S105 (local default, overridden in deployments)
    s3_endpoint_url: str | None = "http://localhost:9000"
    s3_region: str = "eu-central-2"
    s3_access_key: str = "handball"
    s3_secret_key: str = "handball-secret"  # noqa: S105
    s3_bucket_artifacts: str = "artifacts"
    work_dir: str = "/tmp/handball-work"  # noqa: S108

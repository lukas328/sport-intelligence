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

    # Runtime connection uses the non-superuser role so that RLS applies (ADR 005).
    database_url: str = "postgresql+asyncpg://handball_app:handball_app@localhost:5432/handball"
    # Owner connection for migrations only.
    migration_database_url: str | None = None
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

    # Public URL of the web app (links in e-mails)
    web_base_url: str = "http://localhost:3000"

    # Auth (ADR 008)
    secret_key: SecretStr = SecretStr("dev-only-secret-change-me-0123456789abcdef")
    # Fernet key (urlsafe base64, 32 bytes) for encrypting TOTP secrets
    encryption_key: SecretStr = SecretStr("ZGV2LW9ubHktZW5jcnlwdGlvbi1rZXktMzJieXRlcyE=")
    session_cookie: str = "hb_session"
    csrf_cookie: str = "hb_csrf"
    session_ttl_hours: int = 24 * 14
    cookie_secure: bool = False
    magic_link_ttl_minutes: int = 15
    invitation_ttl_days: int = 14
    org_admin_2fa_required: bool = True
    org_admin_2fa_grace_days: int = 14
    password_min_length: int = 10

    # Rate limits: "<count>/<seconds>"
    rate_limit_backend: Literal["redis", "memory"] = "redis"
    rate_limit_auth: str = "10/60"

    # E-mail (ADR 009)
    email_backend: Literal["smtp", "memory", "console"] = "smtp"
    email_from: str = "Handball AI <noreply@localhost>"
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_starttls: bool = False

    max_logo_bytes: int = 1_000_000


@lru_cache
def get_settings() -> Settings:
    return Settings()

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
    # Endpoint the browser uses for presigned uploads (direct to storage, BRIEF 6.2)
    s3_public_endpoint_url: str | None = None
    upload_part_size: int = 16 * 1024 * 1024  # min 5 MiB (S3), 2 GB = 128 parts
    max_video_bytes: int = 40 * 1024**3
    presign_ttl_s: int = 3600

    # Internal callbacks from workers (never exposed through the web origin)
    internal_token: SecretStr = SecretStr("dev-only-internal-token")

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    sentry_dsn: SecretStr | None = None
    # operator backoffice: e-mail addresses of platform operators (BRIEF M8)
    operator_emails: list[str] = Field(default_factory=list)
    # billing (BRIEF 13): off in development and CI, on in production
    billing_enforce: bool = False
    # annual subscription by Swiss QR bill (addendum 01, 4.10); creditor = the operating company
    # support (addendum 01, 4.11/4.12): adapters stay off without configuration
    support_email: str = "support@handball-ai.ch"
    crisp_website_id: str | None = None
    status_page_url: str | None = None
    status_page_push_url: str | None = None  # provider webhook for component status
    status_page_token: SecretStr | None = None
    help_base_url: str = "https://handball-ai.ch/hilfe"
    raw_video_days: int = 90  # originals reduced to the compressed version after this
    alert_cost_chf_per_match: float = 2.0
    alert_analysis_minutes: float = 45.0
    invoice_creditor_name: str = "Handball AI GmbH"
    invoice_creditor_street: str = "Musterstrasse 1"
    invoice_creditor_pcode: str = "3000"
    invoice_creditor_city: str = "Bern"
    invoice_creditor_country: str = "CH"
    invoice_iban: str = "CH9300762011623852957"  # example IBAN (RF reference); set in deployments
    invoice_uid: str | None = None  # CHE-xxx.xxx.xxx MWST when VAT registered
    invoice_vat_registered: bool = False  # see OPEN_QUESTIONS Q-ADD-3
    invoice_vat_rate_percent: float = 8.1
    invoice_payment_days: int = 30
    invoice_annual_months: int = 10  # annual price = 10 monthly prices (two months free)
    stripe_secret_key: SecretStr | None = None
    stripe_webhook_secret: SecretStr | None = None
    stripe_price_team: str | None = None
    stripe_price_club: str | None = None
    stripe_price_goalkeeper: str | None = None
    # optional: natural-language match summaries via the Claude API (templates are used without it)
    anthropic_api_key: SecretStr | None = None
    # data assistant (5.1): monthly model cost cap when billing limits are off (development)
    assistant_usd_month_unenforced: float = 5.0
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
    # Have I Been Pwned range check on new passwords (k-anonymity); on in production
    pwned_check: bool = False

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
    password_reset_ttl_minutes: int = 60
    email_verify_ttl_hours: int = 72

    # OIDC sign-in (ADR 010). A provider is enabled when its client id is set.
    google_client_id: str | None = None
    google_client_secret: SecretStr | None = None
    apple_client_id: str | None = None  # the Services ID
    apple_team_id: str | None = None
    apple_key_id: str | None = None
    apple_private_key: SecretStr | None = None  # PEM of the .p8 key
    # Overrides for tests / self-hosted IdPs: {"google": {"authorize_url": ..., ...}}
    oidc_overrides: dict[str, dict[str, str]] = Field(default_factory=dict)

    # OpenTelemetry: traces are exported when an OTLP endpoint is set
    otel_endpoint: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()

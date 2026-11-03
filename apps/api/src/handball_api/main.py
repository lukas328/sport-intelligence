from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import structlog
from fastapi import Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from handball_api import __version__
from handball_api.core.config import Settings, get_settings
from handball_api.core.db import dispose_engine, init_engine
from handball_api.core.email import (
    ConsoleEmailSender,
    EmailSender,
    MemoryEmailSender,
    SmtpEmailSender,
)
from handball_api.core.errors import install_error_handlers
from handball_api.core.jobs import EventBus, JobQueue, RedisEventBus, RqJobQueue
from handball_api.core.logging import configure_logging, get_logger
from handball_api.core.oidc import OidcClient
from handball_api.core.ratelimit import MemoryRateLimiter, RateLimiter, RedisRateLimiter
from handball_api.core.storage import ObjectStorage, S3Storage
from handball_api.core.telemetry import instrument_engine, setup_tracing
from handball_api.core.text import ClaudeTextGenerator, TextGenerator
from handball_api.routers import auth, health, internal, matches, orgs, teams
from handball_api.routers import billing as billing_router
from handball_api.routers import events as events_router
from handball_api.routers import family as family_router
from handball_api.routers import feed as feed_router
from handball_api.routers import ops as ops_router
from handball_api.routers import presentations as presentations_router
from handball_api.routers import privacy as privacy_router
from handball_api.routers import scouting as scouting_router
from handball_api.routers import sharing as sharing_router
from handball_api.routers import tactics as tactics_router
from handball_api.routers import tags as tags_router
from handball_api.routers import training as training_router
from handball_api.routers.deps import csrf_protect
from handball_api.services.billing import BillingGateway, StripeGateway


def _init_sentry(settings: Settings) -> None:
    if settings.sentry_dsn is None:
        return
    import sentry_sdk

    sentry_sdk.init(
        dsn=settings.sentry_dsn.get_secret_value(),
        environment=settings.env,
        release=f"handball-api@{__version__}",
        traces_sample_rate=0.1,
        send_default_pii=False,
    )


def _email_sender(settings: Settings) -> EmailSender:
    if settings.email_backend == "memory":
        return MemoryEmailSender()
    if settings.email_backend == "console":
        return ConsoleEmailSender()
    return SmtpEmailSender(
        settings.smtp_host,
        settings.smtp_port,
        settings.email_from,
        settings.smtp_username,
        settings.smtp_password.get_secret_value() if settings.smtp_password else None,
        settings.smtp_starttls,
    )


def _rate_limiter(settings: Settings) -> RateLimiter:
    if settings.rate_limit_backend == "memory":
        return MemoryRateLimiter()
    return RedisRateLimiter(settings.redis_url)


DEV_SECRET_MARKERS = ("dev-only", "ZGV2LW9ubHk")


def check_production_secrets(settings: Settings) -> None:
    """Refuse to start in staging/production with the development secrets from the defaults."""
    if settings.env not in ("staging", "production"):
        return
    weak = [
        name
        for name, value in (
            ("HB_SECRET_KEY", settings.secret_key.get_secret_value()),
            ("HB_ENCRYPTION_KEY", settings.encryption_key.get_secret_value()),
            ("HB_INTERNAL_TOKEN", settings.internal_token.get_secret_value()),
        )
        if any(m in value for m in DEV_SECRET_MARKERS)
    ]
    if weak or not settings.cookie_secure:
        raise RuntimeError(f"insecure production config: {weak or ['HB_COOKIE_SECURE=false']}")


def create_app(
    settings: Settings | None = None,
    *,
    email: EmailSender | None = None,
    storage: ObjectStorage | None = None,
    rate_limiter: RateLimiter | None = None,
    oidc: OidcClient | None = None,
    jobs: JobQueue | None = None,
    events: EventBus | None = None,
    text: TextGenerator | None = None,
    billing: BillingGateway | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    check_production_secrets(settings)
    configure_logging(settings.log_level, settings.log_json)
    _init_sentry(settings)
    log = get_logger("handball_api")

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = init_engine(settings.database_url)
        instrument_engine(app, engine)
        log.info("startup", env=settings.env, version=__version__)
        yield
        await dispose_engine()
        log.info("shutdown")

    app = FastAPI(
        title="Handball AI API",
        version=__version__,
        lifespan=lifespan,
        openapi_url="/v1/openapi.json",
        docs_url="/v1/docs",
        redoc_url=None,
        dependencies=[Depends(csrf_protect)],
    )
    app.state.settings = settings
    app.state.email = email or _email_sender(settings)
    app.state.storage = storage or S3Storage(settings)
    app.state.rate_limiter = rate_limiter or _rate_limiter(settings)
    app.state.oidc = oidc or OidcClient()
    app.state.jobs = jobs or RqJobQueue(settings.redis_url)
    app.state.events = events or RedisEventBus(settings.redis_url)
    app.state.billing = billing or (
        StripeGateway(settings.stripe_secret_key.get_secret_value())
        if settings.stripe_secret_key and settings.stripe_secret_key.get_secret_value()
        else None
    )
    app.state.text = text or (
        ClaudeTextGenerator(settings.anthropic_api_key.get_secret_value())
        if settings.anthropic_api_key and settings.anthropic_api_key.get_secret_value()
        else None
    )
    app.dependency_overrides[get_settings] = lambda: settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["content-type", "x-csrf-token", "x-request-id"],
    )

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        structlog.contextvars.bind_contextvars(request_id=request_id)
        try:
            response = await call_next(request)
        finally:
            structlog.contextvars.clear_contextvars()
        response.headers["x-request-id"] = request_id
        response.headers["x-content-type-options"] = "nosniff"
        response.headers["referrer-policy"] = "strict-origin-when-cross-origin"
        response.headers["x-frame-options"] = "DENY"
        # API data is personal: never cache unless a route says otherwise (media sets its own)
        response.headers.setdefault("cache-control", "no-store")
        if settings.cookie_secure:
            response.headers["strict-transport-security"] = "max-age=63072000; includeSubDomains"
        return response

    install_error_handlers(app)
    setup_tracing(app, settings)
    for r in health.routers():
        app.include_router(r)
    app.include_router(auth.router)
    app.include_router(orgs.router)
    app.include_router(teams.router)
    app.include_router(matches.router)
    app.include_router(events_router.router)
    app.include_router(tactics_router.router)
    app.include_router(training_router.router)
    app.include_router(billing_router.router)
    app.include_router(sharing_router.router)
    app.include_router(ops_router.router)
    app.include_router(privacy_router.router)
    app.include_router(family_router.router)
    app.include_router(tags_router.router)
    app.include_router(feed_router.router)
    app.include_router(scouting_router.router)
    app.include_router(presentations_router.router)
    app.include_router(internal.router)
    return app

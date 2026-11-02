from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from handball_api import __version__
from handball_api.core.config import Settings, get_settings
from handball_api.core.db import dispose_engine, init_engine
from handball_api.core.errors import install_error_handlers
from handball_api.core.logging import configure_logging, get_logger
from handball_api.routers import health


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


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, settings.log_json)
    _init_sentry(settings)
    log = get_logger("handball_api")

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        init_engine(settings.database_url)
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
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
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
        return response

    install_error_handlers(app)
    for r in health.routers():
        app.include_router(r)
    return app

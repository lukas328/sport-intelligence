"""OpenTelemetry tracing (BRIEF 6.2). Active only when HB_OTEL_ENDPOINT is set."""

from __future__ import annotations

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter
from sqlalchemy.ext.asyncio import AsyncEngine

from handball_api import __version__
from handball_api.core.config import Settings


def setup_tracing(app: FastAPI, settings: Settings, exporter: SpanExporter | None = None) -> bool:
    if not settings.otel_endpoint and exporter is None:
        return False
    provider = TracerProvider(
        resource=Resource.create(
            {
                "service.name": settings.service_name,
                "service.version": __version__,
                "deployment.environment": settings.env,
            }
        )
    )
    provider.add_span_processor(
        BatchSpanProcessor(
            exporter or OTLPSpanExporter(endpoint=f"{settings.otel_endpoint}/v1/traces")
        )
    )
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(
        app, tracer_provider=provider, excluded_urls="healthz,readyz"
    )
    app.state.tracer_provider = provider
    return True


def instrument_engine(app: FastAPI, engine: AsyncEngine) -> None:
    provider = getattr(app.state, "tracer_provider", None)
    if provider is not None:
        SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine, tracer_provider=provider)

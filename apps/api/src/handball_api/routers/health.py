from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel

from handball_api import __version__
from handball_api.core.config import Settings, get_settings
from handball_api.services.health import Check, default_checks, run_checks

router = APIRouter(tags=["health"])


class Liveness(BaseModel):
    status: Literal["ok"] = "ok"
    service: str
    version: str


class ComponentStatus(BaseModel):
    name: str
    status: Literal["ok", "error"]
    latency_ms: float
    error: str | None = None


class Readiness(BaseModel):
    status: Literal["ok", "degraded"]
    service: str
    version: str
    env: str
    components: list[ComponentStatus]


def get_checks(settings: Annotated[Settings, Depends(get_settings)]) -> dict[str, Check]:
    return default_checks(settings)


ChecksDep = Annotated[dict[str, Check], Depends(get_checks)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


@router.get("/healthz", response_model=Liveness, summary="Liveness probe")
async def healthz(settings: SettingsDep) -> Liveness:
    return Liveness(service=settings.service_name, version=__version__)


async def _readiness(settings: Settings, checks: dict[str, Check], response: Response) -> Readiness:
    results = await run_checks(checks, settings.readiness_timeout_s)
    ok = all(r.status == "ok" for r in results)
    response.status_code = 200 if ok else 503
    return Readiness(
        status="ok" if ok else "degraded",
        service=settings.service_name,
        version=__version__,
        env=settings.env,
        components=[
            ComponentStatus(
                name=r.name, status=r.status, latency_ms=round(r.latency_ms, 1), error=r.error
            )
            for r in results
        ],
    )


@router.get(
    "/readyz",
    response_model=Readiness,
    summary="Readiness probe (checks Postgres, Redis, object storage)",
    responses={503: {"model": Readiness}},
)
async def readyz(settings: SettingsDep, checks: ChecksDep, response: Response) -> Readiness:
    return await _readiness(settings, checks, response)


v1_router = APIRouter(prefix="/v1", tags=["health"])


@v1_router.get("/health", response_model=Readiness, responses={503: {"model": Readiness}})
async def v1_health(settings: SettingsDep, checks: ChecksDep, response: Response) -> Readiness:
    """Public, versioned system status used by the web status page."""
    return await _readiness(settings, checks, response)


def routers() -> list[APIRouter]:
    return [router, v1_router]

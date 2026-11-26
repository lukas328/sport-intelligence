"""Errors of the web app as the browser saw them (hydration mismatches, uncaught errors), for
finding faults nobody reports: a code, the message and stack, the kind of page and of device.

Nothing personal: no cookies are sent (the browser posts with `credentials: omit`), no names, no
page texts, no user or club ids; ids and numbers in the route and URLs with their query are
masked here again whatever the browser sent. Each browser sends at most five per session; here
at most 30 per address in ten minutes are written, more are dropped without an error. Written as
one log line (`client_error`) that goes to the monitoring of the EU environment.
"""

from __future__ import annotations

import re
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import ConfigDict, Field

from handball_api.core.logging import get_logger
from handball_api.routers.deps import client_ip
from handball_api.schemas.common import ApiModel

log = get_logger("handball_api.client_errors")
router = APIRouter(prefix="/v1", tags=["ops"])

LIMIT = (30, 600)
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
QUERY = re.compile(r"(https?://[^\s?#\"')]+)[?#][^\s\"')]*")
NUMBER = re.compile(r"(?<=/)\d+(?=/|$)")


def mask(text: str) -> str:
    """Ids, e-mail addresses and the query of URLs out of a message or a stack."""
    return QUERY.sub(r"\1", EMAIL.sub("[email]", UUID.sub(":id", text)))


def mask_route(route: str) -> str:
    """The kind of page only: /app/:id/matches/:id/check, never a query."""
    path = route.split("?", 1)[0].split("#", 1)[0]
    return NUMBER.sub(":n", UUID.sub(":id", path))[:200]


class ClientErrorIn(ApiModel):
    # nothing beyond these fields is taken: no room for names or page texts
    model_config = ConfigDict(extra="forbid")

    kind: Literal["react", "error", "rejection"]
    code: int | None = Field(default=None, ge=0, le=9999, description="React's error number")
    message: str = Field(max_length=300)
    stack: str | None = Field(default=None, max_length=3000)
    route: str = Field(max_length=300)
    build: str | None = Field(default=None, max_length=64)
    device: Literal["phone", "tablet", "desktop"]


@router.post("/client-errors", status_code=204)
async def report_client_error(data: ClientErrorIn, request: Request) -> None:
    """An error the web app hit in a browser (nothing personal, see the module text)."""
    if not await request.app.state.rate_limiter.hit(f"client-error:{client_ip(request)}", *LIMIT):
        return
    log.warning(
        "client_error",
        kind=data.kind,
        code=data.code,
        message=mask(data.message),
        stack=mask(data.stack) if data.stack else None,
        route=mask_route(data.route),
        build=data.build,
        device=data.device,
    )

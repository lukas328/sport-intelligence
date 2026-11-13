"""The public entry (no account): find the team and see it from the federation's data. Limited
per IP; only what the federation publishes."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request

from handball_api.core.errors import ProblemError
from handball_api.routers.deps import CtxDep, client_ip
from handball_api.schemas.common import ApiModel
from handball_api.schemas.public_teams import PublicTeamHit, PublicTeamPreview
from handball_api.services import public_teams as service

router = APIRouter(prefix="/v1/public", tags=["public"])
SEARCH_LIMIT = (20, 60)  # per IP and minute: a search may reach handball.ch
PREVIEW_LIMIT = (20, 60)  # per team view two calls: the team first, then its scorers


def per_ip(scope: str, limit: tuple[int, int]) -> Any:
    async def _dep(request: Request) -> None:
        if not await request.app.state.rate_limiter.hit(f"{scope}:{client_ip(request)}", *limit):
            raise ProblemError(429, "rate-limited", "Too many requests, try again later")

    return Depends(_dep)


@router.get(
    "/teams",
    response_model=list[PublicTeamHit],
    dependencies=[per_ip("public-team-search", SEARCH_LIMIT)],
)
async def search_teams(
    ctx: CtxDep, q: Annotated[str, Query(min_length=1, max_length=80)]
) -> list[dict[str, Any]]:
    """Teams of the current season of clubs matching the name or town."""
    return await service.search(ctx, q)


@router.get(
    "/clubs/{club_id}/teams/{official_id}",
    response_model=PublicTeamPreview,
    dependencies=[per_ip("public-team-preview", PREVIEW_LIMIT)],
)
async def team_preview(
    ctx: CtxDep, club_id: int, official_id: int, scorers: bool = True
) -> dict[str, Any]:
    """Last result, rank and table, form, scorers and next game of a team; `scorers=false`
    answers fast without the scorers (the entry asks for them afterwards)."""
    return await service.preview(ctx, club_id, official_id, with_scorers=scorers)


class PublicConfig(ApiModel):
    site_url: str
    support_email: str


@router.get("/config", response_model=PublicConfig)
async def public_config(ctx: CtxDep) -> PublicConfig:
    """Addresses the pages link to (website, support), from the configuration: also before
    sign-in, for the entry and its legal links."""
    s = ctx.settings
    return PublicConfig(site_url=s.site_url.rstrip("/"), support_email=s.support_email)

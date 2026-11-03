"""Support, help and onboarding (addendum 01, 4.11)."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse
from pydantic import Field

from handball_api.routers.deps import AuthedDep, CtxDep, OrgDep
from handball_api.schemas.common import ApiModel
from handball_api.schemas.matches import MatchOut
from handball_api.services import matches as match_service
from handball_api.services import support as service
from handball_api.services.orgs import get_team
from handball_api.services.policies import Action

router = APIRouter(tags=["support"])


class FeedbackIn(ApiModel):
    message: str = Field(min_length=3, max_length=4000)
    page: str | None = Field(default=None, max_length=300)
    match_id: uuid.UUID | None = None
    browser: str | None = Field(default=None, max_length=300)
    screenshot: str | None = Field(default=None, max_length=3_000_000, description="PNG data URL")


class ChecklistItem(ApiModel):
    key: str
    done: bool
    link: str | None


class SupportConfig(ApiModel):
    chat: dict[str, Any] | None
    status_url: str | None
    help_url: str
    support_email: str


@router.post("/v1/orgs/{org_id}/feedback", status_code=204)
async def feedback(data: FeedbackIn, scope: OrgDep) -> None:
    """Feedback button: the message goes to support with page, match, club and browser."""
    await service.feedback(
        scope.ctx,
        scope.user,
        data.message,
        {
            "page": data.page,
            "match": data.match_id,
            "browser": data.browser,
            "club": scope.org.name,
        },
        data.screenshot,
    )


@router.get("/v1/support/config", response_model=SupportConfig)
async def config(auth: AuthedDep) -> SupportConfig:
    s = auth.ctx.settings
    return SupportConfig(
        chat=service.chat_config(auth.ctx, auth.user, auth.user.locale),
        status_url=s.status_page_url,
        help_url=s.help_base_url,
        support_email=s.support_email,
    )


@router.get("/v1/orgs/{org_id}/onboarding/checklist", response_model=list[ChecklistItem])
async def checklist(scope: OrgDep) -> list[dict[str, Any]]:
    return await service.checklist(scope.ctx, scope.org)


@router.post(
    "/v1/orgs/{org_id}/teams/{team_id}/demo-match", response_model=MatchOut, status_code=201
)
async def demo_match(team_id: uuid.UUID, scope: OrgDep) -> MatchOut:
    """A demo match with events to try the analysis views (marked as demo, never counted)."""
    await get_team(scope.ctx, team_id, Action.MATCH_WRITE)
    m = await service.demo_match(scope.ctx, team_id)
    return await match_service.match_out(scope.ctx, m)


@router.get("/v1/onboarding/unsubscribe", response_class=HTMLResponse, include_in_schema=False)
async def unsubscribe(
    ctx: CtxDep, u: Annotated[uuid.UUID, Query()], t: Annotated[str, Query(max_length=80)]
) -> HTMLResponse:
    await service.unsubscribe(ctx, u, t)
    return HTMLResponse(
        "<!doctype html><html lang=de><meta charset=utf-8><title>Abgemeldet</title>"
        "<body style='font-family:system-ui;max-width:32rem;margin:4rem auto;padding:0 1rem'>"
        "<h1>Abgemeldet</h1><p>Du bekommst keine weiteren Tipps per E-Mail. "
        "Wichtige Nachrichten zu deinem Konto erhältst du weiterhin.</p></body></html>"
    )

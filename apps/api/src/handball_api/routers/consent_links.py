from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import Field

from handball_api.models.enums import ConsentGivenBy, ConsentKind
from handball_api.routers.deps import CtxDep, OrgDep, rate_limit
from handball_api.schemas.common import ApiModel
from handball_api.services import consent_links as service

router = APIRouter(tags=["consents"])


class ConsentLinkOut(ApiModel):
    id: uuid.UUID
    expires_at: datetime
    answers: int = Field(description="consents that came in through the link")
    created_at: datetime


class ConsentLinkCreated(ConsentLinkOut):
    token: str = Field(description="shown once; the page is /einwilligung/<token>")


class PublicPlayer(ApiModel):
    id: uuid.UUID
    label: str = Field(description="number, first name, initial; never a last name")


class PublicConsentPage(ApiModel):
    club: str
    team: str
    youth: bool
    purposes: list[ConsentKind]
    players: list[PublicPlayer]
    expires_at: datetime


class ConsentAnswer(ApiModel):
    player_id: uuid.UUID
    given_by: ConsentGivenBy
    given_by_name: str = Field(min_length=2, max_length=160)
    agreed: list[ConsentKind] = Field(
        default_factory=list, description="purposes agreed to; the others asked are withdrawn"
    )


@router.get("/v1/orgs/{org_id}/teams/{team_id}/consent-link", response_model=ConsentLinkOut | None)
async def get_link(team_id: uuid.UUID, scope: OrgDep) -> Any:
    """The team's active consent link (without its token), or null."""
    return await service.status(scope.ctx, team_id)


@router.post(
    "/v1/orgs/{org_id}/teams/{team_id}/consent-link",
    response_model=ConsentLinkCreated,
    status_code=201,
)
async def create_link(team_id: uuid.UUID, scope: OrgDep) -> Any:
    """A new link for the team chat (90 days); the previous one stops working."""
    link, token = await service.create(scope.ctx, team_id)
    return {**ConsentLinkOut.model_validate(link).model_dump(), "token": token}


@router.delete("/v1/orgs/{org_id}/teams/{team_id}/consent-link", status_code=204)
async def revoke_link(team_id: uuid.UUID, scope: OrgDep) -> None:
    await service.revoke(scope.ctx, team_id)


@router.get(
    "/v1/consent/{token}",
    response_model=PublicConsentPage,
    dependencies=[Depends(rate_limit("consent"))],
)
async def public_page(token: str, ctx: CtxDep) -> Any:
    """What the public consent page shows (no sign-in)."""
    return await service.public(ctx, token)


@router.post(
    "/v1/consent/{token}",
    response_model=dict[str, Any],
    dependencies=[Depends(rate_limit("consent"))],
)
async def answer(token: str, data: ConsentAnswer, ctx: CtxDep) -> Any:
    """A player (adult) or a parent or guardian answers for one player."""
    return await service.answer(
        ctx, token, data.player_id, data.given_by, data.given_by_name, data.agreed
    )

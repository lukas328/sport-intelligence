"""Official league data (docs/plans/federation-onboarding.md): team search and claim, sync and
suggestions, join requests of players, access requests to a claimed club, club verification."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Query, Response, status

from handball_api.core.db import enable_system_access
from handball_api.models import JoinRequest, OfficialSuggestion, OrgAccessRequest
from handball_api.routers.deps import AuthedDep, OrgDep, per_user
from handball_api.routers.ops import OperatorDep
from handball_api.schemas.official import (
    AccessApproveIn,
    AccessRequestOut,
    ClaimIn,
    ClaimOut,
    JoinApproveIn,
    JoinRequestIn,
    JoinRequestOut,
    MatchCandidate,
    MyAccessRequestOut,
    MyJoinRequestOut,
    OfficialLinkOut,
    OfficialPreferencesIn,
    OfficialTeamHit,
    OperatorVerifyIn,
    SuggestionAcceptIn,
    SuggestionOut,
    SuggestionResultOut,
    SyncOut,
    VerificationOut,
)
from handball_api.services import join_requests, org_verification
from handball_api.services import official as service

router = APIRouter(prefix="/v1", tags=["official"])
SEARCH_LIMIT = (30, 60)  # per user and minute: the search may reach handball.ch
JOIN_LIMIT = (10, 3600)
SYNC_LIMIT = (6, 3600)  # sync now: each one asks handball.ch again
CLAIM_LIMIT = (10, 3600)  # may ask handball.ch, and an access request notifies the club admins


# ---- search and claim (signed in, no club needed) ----------------------------------------------


@router.get(
    "/official/teams",
    response_model=list[OfficialTeamHit],
    dependencies=[per_user("official-search", SEARCH_LIMIT)],
)
async def search_teams(
    auth: AuthedDep, q: Annotated[str, Query(min_length=1, max_length=80)]
) -> list[dict[str, Any]]:
    """Registered teams of the current season of clubs matching the name or town."""
    return await service.search(auth.ctx, auth.user, q)


@router.post(
    "/official/teams/{official_id}/claim",
    response_model=ClaimOut,
    status_code=status.HTTP_201_CREATED,
    responses={202: {"model": ClaimOut}, 200: {"model": ClaimOut}},
    dependencies=[per_user("official-claim", CLAIM_LIMIT)],
)
async def claim_team(
    official_id: int, data: ClaimIn, auth: AuthedDep, response: Response
) -> dict[str, Any]:
    """Take over a registered team: 201 claimed (club and team created or linked, prefilled),
    202 access requested (the club or team is already in the app), 200 already a member."""
    out = await service.claim(auth.ctx, auth.user, official_id, data)
    if out["status"] == "access_requested":
        response.status_code = status.HTTP_202_ACCEPTED
    elif out["status"] == "already_member":
        response.status_code = status.HTTP_200_OK
    return out


# ---- join requests -----------------------------------------------------------------------------


@router.post(
    "/teams/{team_id}/join-requests",
    response_model=MyJoinRequestOut,
    status_code=status.HTTP_201_CREATED,
    tags=["join-requests"],
    dependencies=[per_user("join-request", JOIN_LIMIT)],
)
async def request_join(
    team_id: uuid.UUID, data: JoinRequestIn, auth: AuthedDep
) -> MyJoinRequestOut:
    req = await join_requests.create(auth.ctx, auth.user, team_id, data)
    rows = [r for r in await join_requests.mine(auth.ctx, auth.user) if r[0].id == req.id]
    return _my_join(*rows[0])


def _my_join(req: JoinRequest, team: Any, org: Any) -> MyJoinRequestOut:
    return MyJoinRequestOut(
        id=req.id,
        team_id=req.team_id,
        team_name=team.name,
        organization_id=org.id,
        organization_name=org.name,
        status=req.status,
        created_at=req.created_at,
    )


@router.get("/me/join-requests", response_model=list[MyJoinRequestOut], tags=["join-requests"])
async def my_join_requests(auth: AuthedDep) -> list[MyJoinRequestOut]:
    return [_my_join(*r) for r in await join_requests.mine(auth.ctx, auth.user)]


@router.delete(
    "/me/join-requests/{request_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["join-requests"]
)
async def withdraw_join_request(request_id: uuid.UUID, auth: AuthedDep) -> None:
    await join_requests.withdraw(auth.ctx, auth.user, request_id)


def _join_out(req: JoinRequest, email: str, match: dict[str, Any] | None) -> JoinRequestOut:
    return JoinRequestOut(
        id=req.id,
        team_id=req.team_id,
        user_id=req.user_id,
        email=email,
        first_name=req.first_name,
        last_name=req.last_name,
        jersey_number=req.jersey_number,
        role=req.role,
        message=req.message,
        status=req.status,
        created_at=req.created_at,
        suggested=MatchCandidate(**match) if match else None,
        player_id=req.player_id,
    )


@router.get(
    "/orgs/{org_id}/teams/{team_id}/join-requests",
    response_model=list[JoinRequestOut],
    tags=["join-requests"],
)
async def list_join_requests(team_id: uuid.UUID, scope: OrgDep) -> list[JoinRequestOut]:
    return [_join_out(*r) for r in await join_requests.list_for_team(scope.ctx, team_id)]


@router.post(
    "/orgs/{org_id}/teams/{team_id}/join-requests/{request_id}/approve",
    response_model=JoinRequestOut,
    tags=["join-requests"],
)
async def approve_join_request(
    team_id: uuid.UUID, request_id: uuid.UUID, scope: OrgDep, data: JoinApproveIn | None = None
) -> JoinRequestOut:
    req = await join_requests.approve(scope.ctx, team_id, request_id, data or JoinApproveIn())
    return _join_out(req, "", None)


@router.post(
    "/orgs/{org_id}/teams/{team_id}/join-requests/{request_id}/decline",
    response_model=JoinRequestOut,
    tags=["join-requests"],
)
async def decline_join_request(
    team_id: uuid.UUID, request_id: uuid.UUID, scope: OrgDep
) -> JoinRequestOut:
    return _join_out(await join_requests.decline(scope.ctx, team_id, request_id), "", None)


# ---- team link, sync and suggestions -----------------------------------------------------------


@router.get("/orgs/{org_id}/teams/{team_id}/official", response_model=OfficialLinkOut)
async def team_official(team_id: uuid.UUID, scope: OrgDep) -> dict[str, Any]:
    """Link to the official data, the standing of the group and the open suggestions."""
    return await service.link(scope.ctx, team_id)


@router.patch("/orgs/{org_id}/teams/{team_id}/official", response_model=OfficialLinkOut)
async def team_official_preferences(
    team_id: uuid.UUID, data: OfficialPreferencesIn, scope: OrgDep
) -> dict[str, Any]:
    """Organisers: show the official statistics in roster suggestions or not (roster_stats)."""
    return await service.set_preferences(scope.ctx, team_id, data.roster_stats)


@router.post(
    "/orgs/{org_id}/teams/{team_id}/official/sync",
    response_model=SyncOut,
    dependencies=[per_user("official-sync", SYNC_LIMIT)],
)
async def sync_team(team_id: uuid.UUID, scope: OrgDep) -> dict[str, Any]:
    """Sync now (otherwise daily): changes come in as suggestions."""
    return await service.sync_now(scope.ctx, team_id)


@router.get(
    "/orgs/{org_id}/teams/{team_id}/official/suggestions", response_model=list[SuggestionOut]
)
async def list_suggestions(
    team_id: uuid.UUID,
    scope: OrgDep,
    status_: Annotated[str | None, Query(alias="status", pattern="^(open|accepted|dismissed)$")] = (
        "open"
    ),
    kind: Annotated[str | None, Query(max_length=20)] = None,
) -> list[dict[str, Any]]:
    return await service.list_suggestions(scope.ctx, team_id, status_, kind)


@router.post(
    "/orgs/{org_id}/teams/{team_id}/official/suggestions/{suggestion_id}/accept",
    response_model=SuggestionResultOut,
)
async def accept_suggestion(
    team_id: uuid.UUID,
    suggestion_id: uuid.UUID,
    scope: OrgDep,
    data: SuggestionAcceptIn | None = None,
) -> dict[str, Any]:
    return await service.accept(scope.ctx, team_id, suggestion_id, data or SuggestionAcceptIn())


@router.post(
    "/orgs/{org_id}/teams/{team_id}/official/suggestions/{suggestion_id}/dismiss",
    response_model=SuggestionOut,
)
async def dismiss_suggestion(
    team_id: uuid.UUID, suggestion_id: uuid.UUID, scope: OrgDep
) -> OfficialSuggestion:
    return await service.dismiss(scope.ctx, team_id, suggestion_id)


# ---- access requests ---------------------------------------------------------------------------


def _access_out(req: OrgAccessRequest, name: str, email: str) -> AccessRequestOut:
    return AccessRequestOut(
        id=req.id,
        user_id=req.user_id,
        name=name,
        email=email,
        team_id=req.team_id,
        official_team_id=req.official_team_id,
        message=req.message,
        status=req.status,
        created_at=req.created_at,
    )


@router.get(
    "/orgs/{org_id}/access-requests", response_model=list[AccessRequestOut], tags=["organizations"]
)
async def list_access_requests(scope: OrgDep) -> list[AccessRequestOut]:
    return [
        _access_out(r, u.name, u.email) for r, u in await service.list_access_requests(scope.ctx)
    ]


@router.post(
    "/orgs/{org_id}/access-requests/{request_id}/approve",
    response_model=AccessRequestOut,
    tags=["organizations"],
)
async def approve_access_request(
    request_id: uuid.UUID, scope: OrgDep, data: AccessApproveIn | None = None
) -> AccessRequestOut:
    req = await service.approve_access(scope.ctx, scope.org, request_id, data or AccessApproveIn())
    return _access_out(req, "", "")


@router.post(
    "/orgs/{org_id}/access-requests/{request_id}/decline",
    response_model=AccessRequestOut,
    tags=["organizations"],
)
async def decline_access_request(request_id: uuid.UUID, scope: OrgDep) -> AccessRequestOut:
    return _access_out(await service.decline_access(scope.ctx, request_id), "", "")


@router.get("/me/access-requests", response_model=list[MyAccessRequestOut], tags=["organizations"])
async def my_access_requests(auth: AuthedDep) -> list[MyAccessRequestOut]:
    return [
        MyAccessRequestOut(
            id=r.id,
            organization_id=r.organization_id,
            organization_name=name,
            status=r.status,
            created_at=r.created_at,
        )
        for r, name in await service.my_access_requests(auth.ctx, auth.user)
    ]


# ---- verification ------------------------------------------------------------------------------


@router.get("/orgs/{org_id}/verification", response_model=VerificationOut, tags=["organizations"])
async def verification(scope: OrgDep) -> dict[str, Any]:
    """State of the club's verification; the automatic ways (mail domain, federation licence)
    are checked on every call."""
    await org_verification.evaluate(scope.ctx, scope.org)
    return org_verification.status(scope.org)


@router.post(
    "/orgs/{org_id}/verification/confirm", response_model=VerificationOut, tags=["organizations"]
)
async def confirm_verification(scope: OrgDep) -> dict[str, Any]:
    """A second person with a club role (club admin or coach) confirms the club."""
    await org_verification.confirm(scope.ctx, scope.org, scope.user)
    return org_verification.status(scope.org)


@router.post(
    "/ops/organizations/{org_id}/verification", response_model=VerificationOut, tags=["ops"]
)
async def operator_verification(
    org_id: uuid.UUID, data: OperatorVerifyIn, op: OperatorDep
) -> dict[str, Any]:
    await enable_system_access(op.ctx.db, reason="operator verifies a club")
    org = await org_verification.operator_set(op.ctx, org_id, data.verified)
    return org_verification.status(org)

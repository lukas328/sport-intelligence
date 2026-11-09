"""Join requests (docs/plans/federation-onboarding.md, phase 2, way B).

A signed-in person finds the team (official team search) and asks to join. The app looks for the
matching roster entry or roster suggestion (name, shirt number) and shows it to the coach, who
approves with one click: the person joins the club and the team, and the roster entry is linked
to the account. The person never sees the roster: the match is only shown to the organisers.
Parents of youth players still come through the coach (invitation with the child).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from handball_api.core.db import disable_system_access, enable_system_access, set_tenant
from handball_api.core.errors import ProblemError
from handball_api.integrations.handball_ch import fold
from handball_api.models import (
    JoinRequest,
    Membership,
    OfficialSuggestion,
    Organization,
    OrgMembership,
    Player,
    RosterEntry,
    Team,
    User,
)
from handball_api.models.enums import OrgRole, TeamRole
from handball_api.schemas.official import JoinApproveIn, JoinRequestIn
from handball_api.services import audit, official, training
from handball_api.services.context import Ctx
from handball_api.services.orgs import current_seasons, get_team
from handball_api.services.policies import Action

MIN_SCORE = 3  # last name (2) plus the first name's initial or the shirt number


def _now() -> datetime:
    return datetime.now(UTC)


def score(
    first: str, last: str, number: int | None, c_first: str, c_last: str, c_number: int | None
) -> int:
    """How well a request matches a roster entry: last name 2, first name 2 (initial 1), shirt
    number 1."""
    s = 0
    if fold(last) and fold(last) == fold(c_last):
        s += 2
    f, cf = fold(first), fold(c_first)
    if f and f == cf:
        s += 2
    elif f[:1] and f[:1] == cf[:1]:
        s += 1
    if number is not None and number == c_number:
        s += 1
    return s


async def _candidates(ctx: Ctx, team: Team) -> list[dict[str, Any]]:
    """Unlinked roster entries of the current season and open roster suggestions."""
    out: list[dict[str, Any]] = []
    season = (await current_seasons(ctx, [team.id])).get(team.id)
    if season is not None:
        for e, p in await ctx.db.execute(
            select(RosterEntry, Player)
            .join(Player, Player.id == RosterEntry.player_id)
            .where(RosterEntry.season_id == season.id, Player.user_id.is_(None))
        ):
            out.append(
                {
                    "kind": "player",
                    "id": p.id,
                    "first_name": p.first_name,
                    "last_name": p.last_name,
                    "jersey_number": e.jersey_number,
                }
            )
    for s in await ctx.db.scalars(
        select(OfficialSuggestion).where(
            OfficialSuggestion.team_id == team.id,
            OfficialSuggestion.kind == "roster_add",
            OfficialSuggestion.status == "open",
        )
    ):
        out.append(
            {
                "kind": "suggestion",
                "id": s.id,
                "first_name": str(s.payload.get("first_name") or ""),
                "last_name": str(s.payload.get("last_name") or ""),
                "jersey_number": s.payload.get("jersey_number"),
            }
        )
    return out


def best_match(data: JoinRequestIn, candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    scored = [
        (
            score(
                data.first_name,
                data.last_name,
                data.jersey_number,
                c["first_name"],
                c["last_name"],
                c["jersey_number"],
            ),
            i,
            c,
        )
        for i, c in enumerate(candidates)
    ]
    scored = [x for x in scored if x[0] >= MIN_SCORE]
    if not scored:
        return None
    scored.sort(key=lambda x: (-x[0], x[1]))
    if len(scored) > 1 and scored[0][0] == scored[1][0]:
        return None  # two equally good entries: the coach chooses
    return scored[0][2]


async def create(ctx: Ctx, user: User, team_id: uuid.UUID, data: JoinRequestIn) -> JoinRequest:
    # System path: the person is not a member of the club yet.
    await enable_system_access(ctx.db, reason="join request by a future member")
    try:
        team = await ctx.db.get(Team, team_id)
        if team is None:
            raise ProblemError(404, "not-found", "Team not found")
        member = await ctx.db.scalar(
            select(Membership.id).where(
                Membership.team_id == team.id, Membership.user_id == user.id
            )
        )
        if member is not None:
            raise ProblemError(409, "already-member", "You are already in this team")
        pending = await ctx.db.scalar(
            select(JoinRequest.id).where(
                JoinRequest.team_id == team.id,
                JoinRequest.user_id == user.id,
                JoinRequest.status == "pending",
            )
        )
        if pending is not None:
            raise ProblemError(409, "join-request-pending", "Your request is already waiting")
        match = best_match(data, await _candidates(ctx, team))
        req = JoinRequest(
            organization_id=team.organization_id,
            team_id=team.id,
            user_id=user.id,
            first_name=data.first_name,
            last_name=data.last_name,
            jersey_number=data.jersey_number,
            role=data.role,
            message=data.message,
            suggested_player_id=match["id"] if match and match["kind"] == "player" else None,
            suggested_suggestion_id=(
                match["id"] if match and match["kind"] == "suggestion" else None
            ),
        )
        ctx.db.add(req)
        await ctx.db.flush()
        organisers = (
            await ctx.db.scalars(
                select(Membership.user_id).where(
                    Membership.team_id == team.id,
                    Membership.role.in_([TeamRole.COACH, TeamRole.TEAM_MANAGER]),
                )
            )
        ).all()
        await training.notify(
            ctx,
            team.organization_id,
            list(organisers),
            "join_request",
            {"team_id": str(team.id), "request_id": str(req.id)},
            f"/app/{team.organization_id}/teams/{team.id}/join-requests",
        )
        await audit.record(
            ctx,
            "join_request.created",
            org_id=team.organization_id,
            target_type="join_request",
            target_id=req.id,
            actor_id=user.id,
            data={"team_id": str(team.id), "matched": match["kind"] if match else None},
        )
        return req
    finally:
        await disable_system_access(ctx.db)


async def mine(ctx: Ctx, user: User) -> list[tuple[JoinRequest, Team, Organization]]:
    await enable_system_access(ctx.db, reason="own join requests")
    try:
        rows = await ctx.db.execute(
            select(JoinRequest, Team, Organization)
            .join(Team, Team.id == JoinRequest.team_id)
            .join(Organization, Organization.id == JoinRequest.organization_id)
            .where(JoinRequest.user_id == user.id)
            .order_by(JoinRequest.created_at.desc())
        )
        return [(r, t, o) for r, t, o in rows]
    finally:
        await disable_system_access(ctx.db)


async def withdraw(ctx: Ctx, user: User, request_id: uuid.UUID) -> None:
    await enable_system_access(ctx.db, reason="withdraw own join request")
    try:
        req = await ctx.db.get(JoinRequest, request_id)
        if req is None or req.user_id != user.id:
            raise ProblemError(404, "not-found", "Request not found")
        if req.status != "pending":
            raise ProblemError(409, "request-decided", "This request was already decided")
        req.status, req.decided_at = "withdrawn", _now()
        await audit.record(
            ctx,
            "join_request.withdrawn",
            org_id=req.organization_id,
            target_type="join_request",
            target_id=req.id,
            actor_id=user.id,
        )
    finally:
        await disable_system_access(ctx.db)


async def list_for_team(
    ctx: Ctx, team_id: uuid.UUID
) -> list[tuple[JoinRequest, str, dict[str, Any] | None]]:
    """Pending requests with the requester's e-mail and the suggested roster match."""
    team = await get_team(ctx, team_id, Action.JOIN_REQUESTS_MANAGE)
    rows = (
        await ctx.db.execute(
            select(JoinRequest, User.email)
            .join(User, User.id == JoinRequest.user_id)
            .where(JoinRequest.team_id == team.id, JoinRequest.status == "pending")
            .order_by(JoinRequest.created_at)
        )
    ).all()
    candidates = {c["id"]: c for c in await _candidates(ctx, team)}
    out = []
    for req, email in rows:
        key = req.suggested_player_id or req.suggested_suggestion_id
        out.append((req, email, candidates.get(key) if key else None))
    return out


async def _pending(ctx: Ctx, team_id: uuid.UUID, request_id: uuid.UUID) -> tuple[Team, JoinRequest]:
    team = await get_team(ctx, team_id, Action.JOIN_REQUESTS_MANAGE)
    req = await ctx.db.get(JoinRequest, request_id)
    if req is None or req.team_id != team.id:
        raise ProblemError(404, "not-found", "Request not found")
    if req.status != "pending":
        raise ProblemError(409, "request-decided", "This request was already decided")
    return team, req


async def _player_of(ctx: Ctx, team: Team, req: JoinRequest, data: JoinApproveIn) -> Player:
    if data.new_entry:
        player_id, suggestion_id = None, None
    elif data.player_id or data.suggestion_id:
        player_id, suggestion_id = data.player_id, data.suggestion_id
    else:
        player_id, suggestion_id = req.suggested_player_id, req.suggested_suggestion_id
    if suggestion_id is not None:
        s = await ctx.db.get(OfficialSuggestion, suggestion_id)
        if s is None or s.team_id != team.id or s.kind != "roster_add" or s.status != "open":
            raise ProblemError(409, "suggestion-resolved", "The roster suggestion is gone")
        player = await official.add_from_suggestion(
            ctx, team, s, s.payload.get("jersey_number") or req.jersey_number
        )
        s.status, s.resolved_by_id, s.resolved_at = "accepted", ctx.user_id, _now()
        return player
    if player_id is not None:
        found = await ctx.db.scalar(
            select(Player)
            .join(RosterEntry, RosterEntry.player_id == Player.id)
            .where(Player.id == player_id, RosterEntry.team_id == team.id)
            .limit(1)
        )
        if found is None:
            raise ProblemError(404, "not-found", "Player not found in this team")
        if found.user_id is not None and found.user_id != req.user_id:
            raise ProblemError(409, "player-linked", "This player already has an account")
        return found
    season = (await current_seasons(ctx, [team.id])).get(team.id)
    if season is None:
        raise ProblemError(409, "no-season", "The team has no season")
    player = Player(
        organization_id=team.organization_id, first_name=req.first_name, last_name=req.last_name
    )
    ctx.db.add(player)
    await ctx.db.flush()
    free = await official.number_free(ctx, season.id, req.jersey_number)
    ctx.db.add(
        RosterEntry(
            organization_id=team.organization_id,
            player_id=player.id,
            team_id=team.id,
            season_id=season.id,
            jersey_number=free,
            active=True,
        )
    )
    return player


async def approve(
    ctx: Ctx, team_id: uuid.UUID, request_id: uuid.UUID, data: JoinApproveIn
) -> JoinRequest:
    team, req = await _pending(ctx, team_id, request_id)
    player = await _player_of(ctx, team, req, data)
    player.user_id = req.user_id
    await set_tenant(ctx.db, team.organization_id)
    om = await ctx.db.scalar(
        select(OrgMembership).where(
            OrgMembership.organization_id == team.organization_id,
            OrgMembership.user_id == req.user_id,
        )
    )
    if om is None:
        ctx.db.add(
            OrgMembership(
                organization_id=team.organization_id, user_id=req.user_id, role=OrgRole.MEMBER
            )
        )
    known = await ctx.db.scalar(
        select(Membership.id).where(
            Membership.team_id == team.id, Membership.user_id == req.user_id
        )
    )
    if known is None:
        ctx.db.add(
            Membership(
                organization_id=team.organization_id,
                team_id=team.id,
                user_id=req.user_id,
                role=TeamRole(req.role),
            )
        )
    req.status, req.player_id = "approved", player.id
    req.decided_by_id, req.decided_at = ctx.user_id, _now()
    await ctx.db.flush()
    await training.notify(
        ctx,
        team.organization_id,
        [req.user_id],
        "join_approved",
        {"team_id": str(team.id)},
        f"/app/{team.organization_id}",
    )
    await audit.record(
        ctx,
        "join_request.approved",
        target_type="join_request",
        target_id=req.id,
        data={"player_id": str(player.id), "user_id": str(req.user_id)},
    )
    return req


async def decline(ctx: Ctx, team_id: uuid.UUID, request_id: uuid.UUID) -> JoinRequest:
    _, req = await _pending(ctx, team_id, request_id)
    req.status, req.decided_by_id, req.decided_at = "declined", ctx.user_id, _now()
    await audit.record(ctx, "join_request.declined", target_type="join_request", target_id=req.id)
    return req

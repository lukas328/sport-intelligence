"""Search and claim: the registered teams of a club, taken over or asked for (access)."""

from __future__ import annotations

import re
import uuid
from dataclasses import replace
from typing import Any

from sqlalchemy import select, text

from handball_api.core.db import disable_system_access, enable_system_access
from handball_api.core.errors import ProblemError
from handball_api.integrations import handball_ch as ch
from handball_api.models import (
    Membership,
    OrgAccessRequest,
    Organization,
    OrgMembership,
    Team,
    User,
)
from handball_api.models.enums import (
    OrgRole,
    TeamGender,
    TeamRole,
)
from handball_api.schemas.official import ClaimIn
from handball_api.schemas.orgs import OrgCreate
from handball_api.services import (
    audit,
    billing,
    org_verification,
    training,
)
from handball_api.services import orgs as org_service
from handball_api.services.context import Ctx
from handball_api.services.official._base import MAX_CLUBS, MIN_QUERY, PROVIDER, _unavailable
from handball_api.services.official.sync import _season_row, sync_team
from handball_api.services.policies import Action, authorize

# ---- search ------------------------------------------------------------------------------------


def _tokens(q: str) -> list[str]:
    return [t for t in re.split(r"[^\w]+", ch.fold(q)) if t]


async def search(ctx: Ctx, user: User, q: str) -> list[dict[str, Any]]:
    tokens = _tokens(q)
    if len("".join(tokens)) < MIN_QUERY:
        raise ProblemError(422, "query-too-short", "Type at least three letters")
    try:
        season = await ch.current_season(ctx.db)
        found = []
        for c in await ch.clubs(ctx.db):
            text = ch.fold(f"{c.name} {c.city or ''}")
            if all(t in text for t in tokens):
                # clubs whose name starts with the query first, then the town
                found.append((not ch.fold(c.name).startswith(tokens[0]), c.name, c))
        found.sort(key=lambda x: (x[0], x[1]))
        hits: list[dict[str, Any]] = []
        for _, _, c in found[:MAX_CLUBS]:
            detail = await ch.club(ctx.db, c.id, season.id)
            for t in detail.teams if detail else []:
                hits.append(
                    {
                        "official_id": t.id,
                        "name": t.name,
                        "league": t.league,
                        "league_short": t.league_short,
                        "group_name": t.group_name,
                        "season_id": t.season_id,
                        "club": {"id": c.id, "name": c.name, "city": c.city},
                        "registered_club_id": t.club_id,
                        "status": "available",
                    }
                )
    except ch.UpstreamUnavailableError as exc:
        raise _unavailable(exc) from exc
    if not hits:
        return []
    await enable_system_access(ctx.db, reason="official team search: which teams are claimed")
    try:
        linked = {
            tid: (team_id, org_id)
            for tid, team_id, org_id in await ctx.db.execute(
                select(Team.official_team_id, Team.id, Team.organization_id).where(
                    Team.official_provider == PROVIDER,
                    Team.official_team_id.in_([h["official_id"] for h in hits]),
                )
            )
        }
        mine = set(
            (
                await ctx.db.scalars(
                    select(OrgMembership.organization_id).where(OrgMembership.user_id == user.id)
                )
            ).all()
        )
    finally:
        await disable_system_access(ctx.db)
    for h in hits:
        if h["official_id"] in linked:
            team_id, org_id = linked[h["official_id"]]
            h["team_id"] = team_id
            h["status"] = "member" if org_id in mine else "claimed"
            h["organization_id"] = org_id if org_id in mine else None
    return hits


# ---- claim -------------------------------------------------------------------------------------


def gender_of(t: ch.OfficialTeam) -> TeamGender:
    league = ch.fold(t.league)
    if "frauen" in league or "juniorinnen" in league or (t.league_short or "").startswith("F"):
        return TeamGender.WOMEN
    if "mixed" in league or "gemischt" in league:
        return TeamGender.MIXED
    return TeamGender.MEN


def is_youth(t: ch.OfficialTeam) -> bool:
    return "junior" in ch.fold(t.league) or bool(re.match(r"^[MF]?U\d", t.league_short or ""))


async def _request_access(
    ctx: Ctx,
    user: User,
    org_id: uuid.UUID,
    team_id: uuid.UUID | None,
    official_team_id: int,
    message: str | None,
) -> OrgAccessRequest:
    """System access: the person is not a member of the club asked."""
    req = await ctx.db.scalar(
        select(OrgAccessRequest).where(
            OrgAccessRequest.organization_id == org_id,
            OrgAccessRequest.user_id == user.id,
            OrgAccessRequest.status == "pending",
        )
    )
    if req is None:
        req = OrgAccessRequest(
            organization_id=org_id,
            user_id=user.id,
            team_id=team_id,
            official_team_id=official_team_id,
            message=message,
        )
        ctx.db.add(req)
        await ctx.db.flush()
        admins = (
            await ctx.db.scalars(
                select(OrgMembership.user_id).where(
                    OrgMembership.organization_id == org_id,
                    OrgMembership.role == OrgRole.ORG_ADMIN,
                )
            )
        ).all()
        await training.notify(
            ctx,
            org_id,
            list(admins),
            "access_request",
            # who asks for which team: the admins decide on the Team page (K17)
            {
                "request_id": str(req.id),
                "name": user.name,
                "team": (await ctx.db.get(Team, team_id)).name if team_id else "",  # type: ignore[union-attr]
            },
            f"/app/{org_id}/teams/{team_id}" if team_id else f"/app/{org_id}/club/federation",
        )
        await audit.record(
            ctx,
            "org.access_requested",
            org_id=org_id,
            target_type="org_access_request",
            target_id=req.id,
            actor_id=user.id,
            data={"official_team_id": official_team_id},
        )
    return req


async def _official_team(
    ctx: Ctx, club_id: int, official_team_id: int
) -> tuple[ch.Season, ch.ClubDetail, ch.OfficialTeam]:
    try:
        season = await ch.current_season(ctx.db)
        detail = await ch.club(ctx.db, club_id, season.id)
    except ch.UpstreamUnavailableError as exc:
        raise _unavailable(exc) from exc
    team = next((t for t in detail.teams if t.id == official_team_id), None) if detail else None
    if detail is None or team is None:
        raise ProblemError(404, "official-team-not-found", "This team is not registered there")
    return season, detail, team


async def claim(ctx: Ctx, user: User, official_team_id: int, data: ClaimIn) -> dict[str, Any]:
    season, detail, oteam = await _official_team(ctx, data.club_id, official_team_id)
    # two people claiming the same club at the same moment: the second waits here until the first
    # committed, then finds the club taken and gets an access request (not a unique-key error)
    await ctx.db.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:k))"),
        {"k": f"official-club:{PROVIDER}:{detail.id}"},
    )
    await enable_system_access(ctx.db, reason="official claim: one club per official club id")
    try:
        mine = set(
            (
                await ctx.db.scalars(
                    select(OrgMembership.organization_id).where(OrgMembership.user_id == user.id)
                )
            ).all()
        )
        linked = await ctx.db.scalar(
            select(Team).where(
                Team.official_provider == PROVIDER, Team.official_team_id == official_team_id
            )
        )
        if linked is not None:
            if linked.organization_id in mine:
                return {
                    "status": "already_member",
                    "organization_id": linked.organization_id,
                    "team_id": linked.id,
                }
            req = await _request_access(
                ctx, user, linked.organization_id, linked.id, official_team_id, data.message
            )
            return {"status": "access_requested", "access_request_id": req.id}
        club_org = await ctx.db.scalar(
            select(Organization).where(
                Organization.official_provider == PROVIDER,
                Organization.official_club_id == detail.id,
            )
        )
        if club_org is not None and club_org.id not in mine:
            req = await _request_access(
                ctx, user, club_org.id, None, official_team_id, data.message
            )
            return {"status": "access_requested", "access_request_id": req.id}
    finally:
        await disable_system_access(ctx.db)

    created = False
    if club_org is not None:
        org = club_org
    elif data.org_id is not None:
        actor, org = await org_service.build_actor(ctx, user, data.org_id)
        ctx.actor = actor
        authorize(actor, Action.ORG_UPDATE, two_factor=ctx.two_factor)
        if org.official_club_id is not None:
            raise ProblemError(409, "org-linked", "This club is linked to another official club")
    else:
        org = await org_service.create_org(ctx, user, OrgCreate(name=detail.name[:120]))
        created = True
    if org.official_club_id is None:
        org.official_provider, org.official_club_id = PROVIDER, detail.id
        org.official_domains = ch.mail_domains(detail)
        org.verification = org_verification.UNVERIFIED
        org.claimed_by_id = user.id
    actor, org = await org_service.build_actor(ctx, user, org.id)
    ctx.actor = actor
    authorize(actor, Action.TEAM_CREATE, two_factor=ctx.two_factor)
    team = await _create_team(ctx, org, season, oteam, user.id, data.team_name)
    counts = await sync_team(ctx, team, initial=True)
    await org_verification.evaluate(ctx, org)
    await audit.record(
        ctx,
        "official.team_claimed",
        target_type="team",
        target_id=team.id,
        data={"provider": PROVIDER, "club_id": detail.id, "team_id": oteam.id, "new_org": created},
    )
    return {
        "status": "claimed",
        "organization_id": org.id,
        "team_id": team.id,
        "created_organization": created,
        "verification": org.verification,
        "prefill": counts,
    }


async def _create_team(
    ctx: Ctx,
    org: Organization,
    season: ch.Season,
    oteam: ch.OfficialTeam,
    coach_id: uuid.UUID,
    name: str | None = None,
    role: TeamRole = TeamRole.COACH,
) -> Team:
    await billing.check_new_team(ctx, org.id)
    youth = is_youth(oteam)
    team = Team(
        organization_id=org.id,
        name=(name or oteam.name)[:120],
        league=(oteam.league or None) and str(oteam.league)[:120],
        is_youth=youth,
        gender=gender_of(oteam),
        settings={"players_see_team_stats": not youth},
        official_provider=PROVIDER,
        official_team_id=oteam.id,
        official_club_id=oteam.club_id,
        official_group_id=oteam.group_id,
        official_season_id=oteam.season_id,
        official_state={"league": oteam.league, "group_name": oteam.group_name},
    )
    ctx.db.add(team)
    await ctx.db.flush()
    await _season_row(ctx, org.id, team.id, season)
    ctx.db.add(Membership(organization_id=org.id, team_id=team.id, user_id=coach_id, role=role))
    actor = ctx.require_actor()
    if actor.user_id == coach_id:
        ctx.actor = replace(actor, team_roles={**actor.team_roles, team.id: role})
    await audit.record(ctx, "team.created", target_type="team", target_id=team.id)
    await ctx.db.flush()
    return team

"""Organisations, teams, seasons and memberships."""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import UTC, date, datetime

from sqlalchemy import select

from handball_api.core.db import disable_system_access, enable_system_access, set_tenant
from handball_api.core.errors import ProblemError
from handball_api.core.storage import ObjectNotFoundError
from handball_api.models import Membership, Organization, OrgMembership, Season, Team, User
from handball_api.models.enums import OrgRole, TeamRole
from handball_api.schemas.orgs import (
    OrgCreate,
    OrgUpdate,
    SeasonCreate,
    TeamCreate,
    TeamMemberUpdate,
    TeamUpdate,
)
from handball_api.services import audit
from handball_api.services.context import Ctx
from handball_api.services.policies import Action, Actor, authorize, visible_team_ids

LOGO_TYPES = {
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"\xff\xd8\xff": "image/jpeg",
    b"RIFF": "image/webp",
}


def current_season_bounds(today: date) -> tuple[str, date, date]:
    """Handball seasons run from 1 July to 30 June."""
    start_year = today.year if today.month >= 7 else today.year - 1
    label = f"{start_year}/{str(start_year + 1)[-2:]}"
    return label, date(start_year, 7, 1), date(start_year + 1, 6, 30)


async def create_org(ctx: Ctx, user: User, data: OrgCreate) -> Organization:
    # System path: the organisation does not exist yet, so no tenant context can be set.
    await enable_system_access(ctx.db, reason="organisation creation")
    org = Organization(
        name=data.name,
        country=data.country,
        primary_color=data.primary_color,
        secondary_color=data.secondary_color,
    )
    ctx.db.add(org)
    await ctx.db.flush()
    ctx.db.add(OrgMembership(organization_id=org.id, user_id=user.id, role=OrgRole.ORG_ADMIN))
    await audit.record(
        ctx, "org.created", org_id=org.id, target_type="organization", target_id=org.id
    )
    await ctx.db.flush()
    await disable_system_access(ctx.db)
    await set_tenant(ctx.db, org.id)
    return org


async def list_my_orgs(ctx: Ctx, user: User) -> list[tuple[Organization, OrgRole]]:
    rows = await ctx.db.execute(
        select(Organization, OrgMembership.role)
        .join(OrgMembership, OrgMembership.organization_id == Organization.id)
        .where(OrgMembership.user_id == user.id)
        .order_by(Organization.name)
    )
    return [(o, r) for o, r in rows]


async def build_actor(ctx: Ctx, user: User, org_id: uuid.UUID) -> tuple[Actor, Organization]:
    """Resolve the caller's roles in an organisation. 404 if not a member (no existence leak)."""
    await set_tenant(ctx.db, org_id)
    row = (
        await ctx.db.execute(
            select(Organization, OrgMembership.role)
            .join(OrgMembership, OrgMembership.organization_id == Organization.id)
            .where(Organization.id == org_id, OrgMembership.user_id == user.id)
        )
    ).first()
    if row is None:
        raise ProblemError(404, "not-found", "Organisation not found")
    org, role = row
    team_roles = {
        t: r
        for t, r in (
            await ctx.db.execute(
                select(Membership.team_id, Membership.role).where(Membership.user_id == user.id)
            )
        )
    }
    actor = Actor(
        user_id=user.id,
        organization_id=org.id,
        org_role=role,
        team_roles=team_roles,
        has_2fa=user.totp_enabled,
        org_created_at=org.created_at,
    )
    return actor, org


async def update_org(ctx: Ctx, org: Organization, data: OrgUpdate) -> Organization:
    authorize(ctx.require_actor(), Action.ORG_UPDATE, two_factor=ctx.two_factor)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(org, field, value)
    await audit.record(
        ctx,
        "org.updated",
        target_type="organization",
        target_id=org.id,
        data=data.model_dump(exclude_unset=True),
    )
    return org


def detect_image_type(data: bytes) -> str | None:
    for magic, ctype in LOGO_TYPES.items():
        if data.startswith(magic):
            if ctype == "image/webp" and data[8:12] != b"WEBP":
                return None
            return ctype
    return None


async def set_logo(ctx: Ctx, org: Organization, data: bytes) -> Organization:
    authorize(ctx.require_actor(), Action.ORG_UPDATE, two_factor=ctx.two_factor)
    if len(data) > ctx.settings.max_logo_bytes:
        raise ProblemError(413, "logo-too-large", "The logo must be at most 1 MB")
    ctype = detect_image_type(data)
    if ctype is None:
        raise ProblemError(415, "unsupported-image", "Use PNG, JPEG or WebP")
    key = f"{org.id}/branding/logo-{uuid.uuid4().hex}"
    await ctx.storage.put(ctx.settings.s3_bucket_artifacts, key, data, ctype)
    old = org.logo_key
    org.logo_key = key
    if old:
        await ctx.storage.delete(ctx.settings.s3_bucket_artifacts, old)
    return org


async def get_logo(ctx: Ctx, org: Organization) -> tuple[bytes, str]:
    if not org.logo_key:
        raise ProblemError(404, "not-found", "No logo")
    try:
        return await ctx.storage.get(ctx.settings.s3_bucket_artifacts, org.logo_key)
    except ObjectNotFoundError as exc:
        raise ProblemError(404, "not-found", "No logo") from exc


# ---- teams ---------------------------------------------------------------------------------


async def create_team(ctx: Ctx, data: TeamCreate) -> Team:
    actor = ctx.require_actor()
    authorize(actor, Action.TEAM_CREATE, two_factor=ctx.two_factor)
    team = Team(
        organization_id=actor.organization_id,
        name=data.name,
        league=data.league,
        is_youth=data.is_youth,
        gender=data.gender,
        settings={"players_see_team_stats": not data.is_youth},
    )
    ctx.db.add(team)
    await ctx.db.flush()
    label, start, end = current_season_bounds(datetime.now(UTC).date())
    ctx.db.add(
        Season(
            organization_id=actor.organization_id,
            team_id=team.id,
            label=label,
            starts_on=start,
            ends_on=end,
        )
    )
    if data.join_as_coach:
        ctx.db.add(
            Membership(
                organization_id=actor.organization_id,
                team_id=team.id,
                user_id=actor.user_id,
                role=TeamRole.COACH,
            )
        )
        ctx.actor = replace(actor, team_roles={**actor.team_roles, team.id: TeamRole.COACH})
    await audit.record(ctx, "team.created", target_type="team", target_id=team.id)
    await ctx.db.flush()
    return team


async def list_teams(ctx: Ctx) -> list[Team]:
    actor = ctx.require_actor()
    query = select(Team).order_by(Team.name)
    visible = visible_team_ids(actor)
    if visible is not None:
        query = query.where(Team.id.in_(visible))
    return list((await ctx.db.scalars(query)).all())


async def get_team(ctx: Ctx, team_id: uuid.UUID, action: Action = Action.TEAM_READ) -> Team:
    actor = ctx.require_actor()
    team = await ctx.db.get(Team, team_id)
    if team is None or team.organization_id != actor.organization_id:
        raise ProblemError(404, "not-found", "Team not found")
    if (
        action == Action.TEAM_READ
        and visible_team_ids(actor) is not None
        and not _can_read(actor, team_id)
    ):
        raise ProblemError(404, "not-found", "Team not found")
    authorize(actor, action, team_id, two_factor=ctx.two_factor)
    return team


def _can_read(actor: Actor, team_id: uuid.UUID) -> bool:
    visible = visible_team_ids(actor)
    return visible is None or team_id in visible


async def update_team(ctx: Ctx, team_id: uuid.UUID, data: TeamUpdate) -> Team:
    team = await get_team(ctx, team_id, Action.TEAM_UPDATE)
    values = data.model_dump(exclude_unset=True)
    settings = values.pop("settings", None)
    for field, value in values.items():
        setattr(team, field, value)
    if settings is not None:
        team.settings = {**team.settings, **settings}
    await audit.record(
        ctx,
        "team.updated",
        target_type="team",
        target_id=team.id,
        data=data.model_dump(exclude_unset=True, mode="json"),
    )
    return team


async def delete_team(ctx: Ctx, team_id: uuid.UUID) -> None:
    actor = ctx.require_actor()
    authorize(actor, Action.TEAM_DELETE, two_factor=ctx.two_factor)
    team = await ctx.db.get(Team, team_id)
    if team is None:
        raise ProblemError(404, "not-found", "Team not found")
    await ctx.db.delete(team)
    await audit.record(
        ctx, "team.deleted", target_type="team", target_id=team_id, data={"name": team.name}
    )


async def list_seasons(ctx: Ctx, team_id: uuid.UUID) -> list[Season]:
    await get_team(ctx, team_id)
    rows = await ctx.db.scalars(
        select(Season).where(Season.team_id == team_id).order_by(Season.starts_on.desc())
    )
    return list(rows.all())


async def current_seasons(ctx: Ctx, team_ids: list[uuid.UUID]) -> dict[uuid.UUID, Season]:
    """Current season per team in one query (season containing today, else the latest)."""
    if not team_ids:
        return {}
    today = datetime.now(UTC).date()
    rows = await ctx.db.scalars(
        select(Season).where(Season.team_id.in_(team_ids)).order_by(Season.starts_on.desc())
    )
    result: dict[uuid.UUID, Season] = {}
    current: set[uuid.UUID] = set()
    for s in rows.all():  # newest first
        if s.team_id in current:
            continue
        if s.starts_on <= today <= s.ends_on:
            result[s.team_id] = s
            current.add(s.team_id)
        else:
            result.setdefault(s.team_id, s)
    return result


async def create_season(ctx: Ctx, team_id: uuid.UUID, data: SeasonCreate) -> Season:
    team = await get_team(ctx, team_id, Action.SEASON_WRITE)
    exists = await ctx.db.scalar(
        select(Season.id).where(Season.team_id == team.id, Season.label == data.label)
    )
    if exists:
        raise ProblemError(409, "season-exists", "A season with this label exists")
    season = Season(organization_id=team.organization_id, team_id=team.id, **data.model_dump())
    ctx.db.add(season)
    await ctx.db.flush()
    return season


async def get_season(ctx: Ctx, team_id: uuid.UUID, season_id: uuid.UUID) -> Season:
    season = await ctx.db.get(Season, season_id)
    if season is None or season.team_id != team_id:
        raise ProblemError(404, "not-found", "Season not found")
    return season


# ---- members -------------------------------------------------------------------------------


async def list_org_members(ctx: Ctx) -> list[tuple[User, OrgRole, dict[uuid.UUID, TeamRole]]]:
    actor = ctx.require_actor()
    authorize(actor, Action.ORG_MEMBERS_READ, two_factor=ctx.two_factor)
    rows = await ctx.db.execute(
        select(User, OrgMembership.role)
        .join(OrgMembership, OrgMembership.user_id == User.id)
        .order_by(User.name)
    )
    teams: dict[uuid.UUID, dict[uuid.UUID, TeamRole]] = {}
    for uid, tid, role in await ctx.db.execute(
        select(Membership.user_id, Membership.team_id, Membership.role)
    ):
        teams.setdefault(uid, {})[tid] = role
    return [(u, r, teams.get(u.id, {})) for u, r in rows]


async def list_team_members(ctx: Ctx, team_id: uuid.UUID) -> list[tuple[User, TeamRole]]:
    await get_team(ctx, team_id, Action.TEAM_MEMBERS_READ)
    rows = await ctx.db.execute(
        select(User, Membership.role)
        .join(Membership, Membership.user_id == User.id)
        .where(Membership.team_id == team_id)
        .order_by(User.name)
    )
    return [(u, r) for u, r in rows]


async def _team_membership(ctx: Ctx, team_id: uuid.UUID, user_id: uuid.UUID) -> Membership:
    m = await ctx.db.scalar(
        select(Membership).where(Membership.team_id == team_id, Membership.user_id == user_id)
    )
    if m is None:
        raise ProblemError(404, "not-found", "Member not found")
    return m


async def update_team_member(
    ctx: Ctx, team_id: uuid.UUID, user_id: uuid.UUID, data: TeamMemberUpdate
) -> Membership:
    await get_team(ctx, team_id, Action.TEAM_MEMBERS_MANAGE)
    m = await _team_membership(ctx, team_id, user_id)
    old = m.role
    m.role = data.role
    await audit.record(
        ctx,
        "team.member_role_changed",
        target_type="user",
        target_id=user_id,
        data={"team_id": str(team_id), "from": old, "to": data.role},
    )
    return m


async def remove_team_member(ctx: Ctx, team_id: uuid.UUID, user_id: uuid.UUID) -> None:
    await get_team(ctx, team_id, Action.TEAM_MEMBERS_MANAGE)
    m = await _team_membership(ctx, team_id, user_id)
    await ctx.db.delete(m)
    await audit.record(
        ctx,
        "team.member_removed",
        target_type="user",
        target_id=user_id,
        data={"team_id": str(team_id)},
    )

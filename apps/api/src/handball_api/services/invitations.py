"""Invitations by signed (opaque, hashed) token (BRIEF 6.2)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from handball_api.core.db import disable_system_access, enable_system_access, set_tenant
from handball_api.core.email import try_send
from handball_api.core.errors import ProblemError
from handball_api.core.security import hash_token, new_token
from handball_api.integrations.handball_ch import fold
from handball_api.models import (
    Guardianship,
    Invitation,
    Membership,
    Organization,
    OrgMembership,
    Player,
    RosterEntry,
    Team,
    User,
)
from handball_api.models.enums import OrgRole, TeamRole
from handball_api.schemas.orgs import InvitationCreate, InvitationPreview
from handball_api.services import audit
from handball_api.services.context import Ctx
from handball_api.services.mail_templates import render
from handball_api.services.orgs import current_seasons, get_team
from handball_api.services.policies import Action, authorize


def _now() -> datetime:
    return datetime.now(UTC)


PLAYER_ROLES = (TeamRole.PLAYER, TeamRole.GOALKEEPER)


def _words(s: str) -> str:
    return " ".join(fold(s).split())


async def _free_entries(ctx: Ctx, team: Team) -> list[tuple[RosterEntry, Player]]:
    """Roster entries of the team's current season without an account."""
    season = (await current_seasons(ctx, [team.id])).get(team.id)
    if season is None:
        return []
    rows = await ctx.db.execute(
        select(RosterEntry, Player)
        .join(Player, Player.id == RosterEntry.player_id)
        .where(
            RosterEntry.season_id == season.id,
            RosterEntry.team_id == team.id,
            Player.user_id.is_(None),
        )
    )
    return [(e, p) for e, p in rows]


async def _match_hints(ctx: Ctx, team: Team, data: InvitationCreate) -> uuid.UUID | None:
    """The one free roster entry whose name and shirt number match what the organiser typed
    (every given field must match; a first name alone is not enough)."""
    if data.last_name is None and data.jersey_number is None:
        return None
    found = [
        p.id
        for e, p in await _free_entries(ctx, team)
        if (data.first_name is None or _words(data.first_name) == _words(p.first_name))
        and (data.last_name is None or _words(data.last_name) == _words(p.last_name))
        and (data.jersey_number is None or data.jersey_number == e.jersey_number)
    ]
    return found[0] if len(found) == 1 else None


async def _match_account_name(ctx: Ctx, team: Team, user: User) -> Player | None:
    """The one free roster entry whose full name is the accepting account's name (either
    order); used when the invitation names no entry (an e-mail invitation from onboarding)."""
    name = _words(user.name)
    if not name:
        return None
    found = [
        p
        for _, p in await _free_entries(ctx, team)
        if name
        in (
            _words(f"{p.first_name} {p.last_name}"),
            _words(f"{p.last_name} {p.first_name}"),
        )
    ]
    return found[0] if len(found) == 1 else None


def status_of(inv: Invitation) -> str:
    if inv.accepted_at:
        return "accepted"
    if inv.revoked_at:
        return "revoked"
    if inv.expires_at <= _now():
        return "expired"
    return "pending"


async def create(
    ctx: Ctx, org: Organization, inviter: User, data: InvitationCreate
) -> tuple[Invitation, str]:
    actor = ctx.require_actor()
    team: Team | None = None
    if data.org_role == OrgRole.ORG_ADMIN:
        authorize(actor, Action.INVITE_ORG, two_factor=ctx.two_factor)
    if data.team_id is not None:
        team = await get_team(ctx, data.team_id, Action.INVITE_TEAM)
    if data.team_role == TeamRole.PARENT and data.player_id is None:
        raise ProblemError(422, "parent-needs-player", "A parent invitation names the child")
    player_id = data.player_id
    if player_id is not None:
        if team is None:
            raise ProblemError(422, "player-needs-team", "Linking a player needs a team invitation")
        player = await ctx.db.scalar(
            select(Player)
            .join(RosterEntry, RosterEntry.player_id == Player.id)
            .where(Player.id == player_id, RosterEntry.team_id == team.id)
            .limit(1)
        )
        if player is None:
            raise ProblemError(404, "not-found", "Player not found in this team")
        if data.team_role != TeamRole.PARENT and player.user_id is not None:
            owner = await ctx.db.scalar(select(User.email).where(User.id == player.user_id))
            if (owner or "").lower() != data.email.lower():
                raise ProblemError(409, "player-linked", "This player already has an account")
    elif team is not None and data.team_role in PLAYER_ROLES:
        player_id = await _match_hints(ctx, team, data)
    token = new_token()
    inv = Invitation(
        organization_id=org.id,
        email=data.email,
        token_hash=hash_token(token),
        org_role=data.org_role,
        team_id=data.team_id,
        team_role=data.team_role,
        player_id=player_id,
        invited_by_id=inviter.id,
        expires_at=_now() + timedelta(days=ctx.settings.invitation_ttl_days),
    )
    ctx.db.add(inv)
    await ctx.db.flush()
    # the invitation stays valid when the mail fails (logged); it can be revoked and sent again
    await try_send(
        ctx.email,
        render(
            "invitation",
            inviter.locale,
            to=data.email,
            inviter=inviter.name,
            org=org.name,
            team=f" ({team.name})" if team else "",
            link=f"{ctx.settings.web_base_url}/invite/{token}",
            days=ctx.settings.invitation_ttl_days,
        ),
        "invitation",
        invitation_id=str(inv.id),
    )
    await audit.record(
        ctx,
        "invitation.created",
        target_type="invitation",
        target_id=inv.id,
        data={
            "email": data.email,
            "org_role": data.org_role,
            "team_role": data.team_role,
            "player_id": str(player_id) if player_id else None,
        },
    )
    return inv, token


async def list_for_org(ctx: Ctx, team_id: uuid.UUID | None = None) -> list[Invitation]:
    actor = ctx.require_actor()
    q = select(Invitation).order_by(Invitation.created_at.desc())
    if team_id is not None:
        await get_team(ctx, team_id, Action.INVITE_TEAM)
        q = q.where(Invitation.team_id == team_id)
    else:
        authorize(actor, Action.INVITE_ORG, two_factor=ctx.two_factor)
    return list((await ctx.db.scalars(q)).all())


async def revoke(ctx: Ctx, invitation_id: uuid.UUID) -> Invitation:
    actor = ctx.require_actor()
    inv = await ctx.db.get(Invitation, invitation_id)
    if inv is None:
        raise ProblemError(404, "not-found", "Invitation not found")
    if inv.team_id and inv.org_role != OrgRole.ORG_ADMIN:
        await get_team(ctx, inv.team_id, Action.INVITE_TEAM)
    else:
        authorize(actor, Action.INVITE_ORG, two_factor=ctx.two_factor)
    inv.revoked_at = inv.revoked_at or _now()
    await audit.record(ctx, "invitation.revoked", target_type="invitation", target_id=inv.id)
    return inv


async def _by_token(ctx: Ctx, token: str) -> Invitation:
    # System path: the invitee is not a member yet, the token is the capability.
    await enable_system_access(ctx.db, reason="invitation lookup by token")
    inv = await ctx.db.scalar(select(Invitation).where(Invitation.token_hash == hash_token(token)))
    if inv is None:
        await disable_system_access(ctx.db)
        raise ProblemError(404, "not-found", "Invitation not found")
    return inv


async def preview(ctx: Ctx, token: str) -> InvitationPreview:
    inv = await _by_token(ctx, token)
    org = await ctx.db.get(Organization, inv.organization_id)
    team = await ctx.db.get(Team, inv.team_id) if inv.team_id else None
    account = await ctx.db.scalar(select(User.id).where(User.email == inv.email))
    await disable_system_access(ctx.db)
    assert org is not None
    return InvitationPreview(
        organization_name=org.name,
        team_name=team.name if team else None,
        email=inv.email,
        org_role=inv.org_role,
        team_role=inv.team_role,
        status=status_of(inv),
        account_exists=account is not None,
    )


async def accept(ctx: Ctx, token: str, user: User) -> Organization:
    inv = await _by_token(ctx, token)
    try:
        status = status_of(inv)
        if status != "pending":
            raise ProblemError(410, f"invitation-{status}", f"The invitation is {status}")
        if inv.email.lower() != user.email.lower():
            raise ProblemError(
                403,
                "invitation-email-mismatch",
                "This invitation was sent to a different e-mail address",
            )
        await disable_system_access(ctx.db)
        await set_tenant(ctx.db, inv.organization_id)
        own: Player | None = None
        if inv.player_id and inv.team_role != TeamRole.PARENT:
            # locked: two accounts accepting for the same entry at once cannot both get it
            own = await ctx.db.scalar(
                select(Player).where(Player.id == inv.player_id).with_for_update()
            )
            if own is not None and own.user_id not in (None, user.id):
                raise ProblemError(409, "player-linked", "This player already has an account")
        elif inv.player_id is None and inv.team_id and inv.team_role in PLAYER_ROLES:
            team = await ctx.db.get(Team, inv.team_id)
            if team is not None:
                own = await _match_account_name(ctx, team, user)
                if own is not None:
                    inv.player_id = own.id
        om = await ctx.db.scalar(select(OrgMembership).where(OrgMembership.user_id == user.id))
        if om is None:
            ctx.db.add(
                OrgMembership(
                    organization_id=inv.organization_id, user_id=user.id, role=inv.org_role
                )
            )
        elif inv.org_role == OrgRole.ORG_ADMIN:
            om.role = OrgRole.ORG_ADMIN
        if inv.team_id and inv.team_role:
            m = await ctx.db.scalar(
                select(Membership).where(
                    Membership.team_id == inv.team_id, Membership.user_id == user.id
                )
            )
            if m is None:
                ctx.db.add(
                    Membership(
                        organization_id=inv.organization_id,
                        team_id=inv.team_id,
                        user_id=user.id,
                        role=inv.team_role,
                    )
                )
            else:
                m.role = inv.team_role
        if inv.player_id and inv.team_role == TeamRole.PARENT:
            known = await ctx.db.scalar(
                select(Guardianship.id).where(
                    Guardianship.user_id == user.id, Guardianship.player_id == inv.player_id
                )
            )
            if known is None:
                ctx.db.add(
                    Guardianship(
                        organization_id=inv.organization_id,
                        user_id=user.id,
                        player_id=inv.player_id,
                    )
                )
        elif own is not None:
            own.user_id = user.id
        inv.accepted_at = _now()
        user.email_verified_at = user.email_verified_at or _now()
        await audit.record(
            ctx,
            "invitation.accepted",
            org_id=inv.organization_id,
            target_type="invitation",
            target_id=inv.id,
            actor_id=user.id,
            data={"player_id": str(own.id)} if own is not None else None,
        )
        org = await ctx.db.get(Organization, inv.organization_id)
        assert org is not None
        return org
    finally:
        await disable_system_access(ctx.db)

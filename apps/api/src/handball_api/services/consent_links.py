"""Consent through a link without an account (SPEC section 1): the one thing players and parents
must do in the core product. One link per team, posted in the team chat; a person picks the player
(first name, initial, number), says who they are and which purposes they agree to.

Tokens are random, only their hash is stored; links expire after 90 days and can be revoked. The
public page shows no last names. The rules for consent stay those of roster.add_consent: minors need
a parent or guardian, youth teams never consent to public purposes.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select

from handball_api.core.db import disable_system_access, enable_system_access, set_tenant
from handball_api.core.errors import ProblemError
from handball_api.core.security import hash_token, new_token
from handball_api.models import Consent, ConsentLink, Organization, Player, RosterEntry, Team
from handball_api.models.enums import ConsentGivenBy, ConsentKind
from handball_api.services import audit
from handball_api.services.context import Ctx
from handball_api.services.orgs import current_seasons, get_team
from handball_api.services.policies import Action
from handball_api.services.roster import PUBLIC_PURPOSES, check_consent_giver

VALID_DAYS = 90


def _now() -> datetime:
    return datetime.now(UTC)


def purposes(youth: bool) -> list[ConsentKind]:
    """What the link asks for: analysis and highlights; public purposes only outside youth teams."""
    asked = [ConsentKind.ANALYSIS, ConsentKind.HIGHLIGHTS_INTERNAL, ConsentKind.HIGHLIGHTS_PUBLIC]
    return [k for k in asked if not (youth and k in PUBLIC_PURPOSES)]


async def _active(ctx: Ctx, team_id: uuid.UUID) -> ConsentLink | None:
    return await ctx.db.scalar(
        select(ConsentLink)
        .where(
            ConsentLink.team_id == team_id,
            ConsentLink.revoked_at.is_(None),
            ConsentLink.expires_at > _now(),
        )
        .order_by(ConsentLink.created_at.desc())
        .limit(1)
    )


async def status(ctx: Ctx, team_id: uuid.UUID) -> ConsentLink | None:
    await get_team(ctx, team_id, Action.CONSENT_READ)
    return await _active(ctx, team_id)


async def create(ctx: Ctx, team_id: uuid.UUID) -> tuple[ConsentLink, str]:
    """A new link for the team; the previous one stops working (one link per team)."""
    team = await get_team(ctx, team_id, Action.CONSENT_WRITE)
    season = (await current_seasons(ctx, [team.id])).get(team.id)
    if season is None:
        raise ProblemError(409, "no-season", "The team has no season")
    old = await _active(ctx, team.id)
    if old is not None:
        old.revoked_at = _now()
    token = new_token(24)
    link = ConsentLink(
        organization_id=team.organization_id,
        team_id=team.id,
        season_id=season.id,
        token_hash=hash_token(token),
        expires_at=_now() + timedelta(days=VALID_DAYS),
        answers=0,
        created_by_id=ctx.user_id,
    )
    ctx.db.add(link)
    await ctx.db.flush()
    await audit.record(ctx, "consent_link.created", target_type="team", target_id=team.id)
    return link, token


async def revoke(ctx: Ctx, team_id: uuid.UUID) -> None:
    await get_team(ctx, team_id, Action.CONSENT_WRITE)
    link = await _active(ctx, team_id)
    if link is not None:
        link.revoked_at = _now()
        await audit.record(ctx, "consent_link.revoked", target_type="team", target_id=team_id)


# ---- public side ------------------------------------------------------------------------------


async def _resolve(ctx: Ctx, token: str) -> ConsentLink:
    await enable_system_access(ctx.db, reason="consent link lookup")
    link = await ctx.db.scalar(
        select(ConsentLink).where(ConsentLink.token_hash == hash_token(token))
    )
    await disable_system_access(ctx.db)
    if link is None or link.revoked_at is not None or link.expires_at <= _now():
        raise ProblemError(404, "not-found", "This link is no longer valid")
    await set_tenant(ctx.db, link.organization_id)
    return link


async def _players(ctx: Ctx, link: ConsentLink) -> list[tuple[Player, int | None]]:
    rows = (
        await ctx.db.execute(
            select(Player, RosterEntry.jersey_number)
            .join(RosterEntry, RosterEntry.player_id == Player.id)
            .where(RosterEntry.season_id == link.season_id, RosterEntry.team_id == link.team_id)
            .order_by(RosterEntry.jersey_number.nulls_last(), Player.first_name)
        )
    ).all()
    return [(p, n) for p, n in rows]


def _label(p: Player, number: int | None) -> str:
    initial = f" {p.last_name[:1]}." if p.last_name else ""
    return f"#{number} {p.first_name}{initial}" if number else f"{p.first_name}{initial}"


async def public(ctx: Ctx, token: str) -> dict[str, Any]:
    link = await _resolve(ctx, token)
    team = await ctx.db.get(Team, link.team_id)
    org = await ctx.db.get(Organization, link.organization_id)
    assert team is not None and org is not None
    return {
        "club": org.name,
        "team": team.name,
        "youth": team.is_youth,
        "purposes": purposes(team.is_youth),
        "players": [{"id": str(p.id), "label": _label(p, n)} for p, n in await _players(ctx, link)],
        "expires_at": link.expires_at,
    }


async def answer(
    ctx: Ctx,
    token: str,
    player_id: uuid.UUID,
    given_by: ConsentGivenBy,
    given_by_name: str,
    agreed: list[ConsentKind],
) -> dict[str, Any]:
    """Records the answer: every purpose asked for is granted (a new row) or, when left out,
    withdrawn if it was granted before. The history stays (rows, revoked_at)."""
    link = await _resolve(ctx, token)
    team = await ctx.db.get(Team, link.team_id)
    assert team is not None
    player = next((p for p, _ in await _players(ctx, link) if p.id == player_id), None)
    if player is None:
        raise ProblemError(404, "not-found", "Player not in this team")
    now = _now()
    check_consent_giver(player, given_by, now, team.is_youth)
    asked = purposes(team.is_youth)
    if any(k not in asked for k in agreed):
        raise ProblemError(403, "youth-protection", "This purpose is not asked for this team")
    active = {
        c.kind: c
        for c in (
            await ctx.db.scalars(
                select(Consent).where(Consent.player_id == player.id, Consent.revoked_at.is_(None))
            )
        ).all()
    }
    for kind in asked:
        if kind in agreed and kind not in active:
            ctx.db.add(
                Consent(
                    organization_id=link.organization_id,
                    player_id=player.id,
                    kind=kind,
                    given_by=given_by,
                    given_by_name=given_by_name,
                    given_at=now,
                    document_ref="consent link",
                )
            )
        elif kind not in agreed and kind in active:
            active[kind].revoked_at = now
    link.answers += 1
    await ctx.db.flush()
    await audit.record(
        ctx,
        "consent.recorded_by_link",
        org_id=link.organization_id,
        target_type="player",
        target_id=player.id,
        data={"agreed": [str(k) for k in agreed], "given_by": str(given_by)},
    )
    return {"player": _label(player, None), "agreed": agreed}

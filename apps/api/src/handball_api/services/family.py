"""Own consents (addendum 01, P6): adult players decide for themselves, parents for their children.

A parent (team role `parent`, linked by a guardianship) sees only their own children and the
consents per purpose. Consents are history rows: giving a consent adds a row, revoking sets
`revoked_at`; the latest unrevoked row of a purpose counts.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import select

from handball_api.core.errors import ProblemError
from handball_api.models import Consent, Guardianship, Player, RosterEntry, Team
from handball_api.models.enums import ConsentGivenBy, ConsentKind
from handball_api.services import audit
from handball_api.services.context import Ctx
from handball_api.services.roster import check_consent_giver, check_youth_purpose, is_minor


@dataclass
class Subject:
    player: Player
    relation: str  # "self" | "guardian"
    teams: list[Team] = field(default_factory=list)
    consents: list[Consent] = field(default_factory=list)
    minor: bool | None = None


def _now() -> datetime:
    return datetime.now(UTC)


async def _subject_ids(ctx: Ctx) -> dict[uuid.UUID, str]:
    user_id = ctx.user_id
    if user_id is None:
        raise ProblemError(401, "unauthenticated", "Sign in first")
    own = (await ctx.db.scalars(select(Player.id).where(Player.user_id == user_id))).all()
    kids = (
        await ctx.db.scalars(select(Guardianship.player_id).where(Guardianship.user_id == user_id))
    ).all()
    out = {pid: "guardian" for pid in kids}
    out.update({pid: "self" for pid in own})
    return out


async def subjects(ctx: Ctx) -> list[Subject]:
    ids = await _subject_ids(ctx)
    if not ids:
        return []
    players = (await ctx.db.scalars(select(Player).where(Player.id.in_(ids)))).all()
    teams = (
        await ctx.db.execute(
            select(RosterEntry.player_id, Team)
            .join(Team, Team.id == RosterEntry.team_id)
            .where(RosterEntry.player_id.in_(ids), RosterEntry.active)
        )
    ).all()
    consents = (
        await ctx.db.scalars(
            select(Consent).where(Consent.player_id.in_(ids)).order_by(Consent.given_at.desc())
        )
    ).all()
    now = _now()
    out = []
    for p in sorted(players, key=lambda p: (ids[p.id] != "self", p.first_name)):
        seen: set[uuid.UUID] = set()
        team_list = []
        for pid, t in teams:
            if pid == p.id and t.id not in seen:
                seen.add(t.id)
                team_list.append(t)
        out.append(
            Subject(
                player=p,
                relation=ids[p.id],
                teams=team_list,
                consents=[c for c in consents if c.player_id == p.id],
                minor=is_minor(p.birth_year, now),
            )
        )
    return out


async def _subject(ctx: Ctx, player_id: uuid.UUID) -> tuple[Player, str]:
    relation = (await _subject_ids(ctx)).get(player_id)
    player = await ctx.db.get(Player, player_id) if relation else None
    if player is None or relation is None:
        raise ProblemError(404, "not-found", "Player not found")
    return player, relation


async def give(ctx: Ctx, player_id: uuid.UUID, kind: ConsentKind, name: str) -> Consent:
    player, relation = await _subject(ctx, player_id)
    given_by = ConsentGivenBy.SELF if relation == "self" else ConsentGivenBy.PARENT
    youth = (
        await ctx.db.scalar(
            select(Team.id)
            .join(RosterEntry, RosterEntry.team_id == Team.id)
            .where(RosterEntry.player_id == player.id, Team.is_youth)
            .limit(1)
        )
    ) is not None
    now = _now()
    check_consent_giver(player, given_by, now, youth)
    check_youth_purpose(kind, youth or bool(is_minor(player.birth_year, now)))
    active = await ctx.db.scalar(
        select(Consent).where(
            Consent.player_id == player.id, Consent.kind == kind, Consent.revoked_at.is_(None)
        )
    )
    if active is not None:
        return active
    consent = Consent(
        organization_id=player.organization_id,
        player_id=player.id,
        kind=kind,
        given_by=given_by,
        given_by_name=name[:160],
        given_at=now,
        recorded_by_id=ctx.user_id,
    )
    ctx.db.add(consent)
    await ctx.db.flush()
    await audit.record(
        ctx,
        "consent.given_online",
        target_type="player",
        target_id=player.id,
        data={"kind": kind, "by": given_by},
    )
    return consent


async def revoke(ctx: Ctx, player_id: uuid.UUID, kind: ConsentKind) -> int:
    """Revoking is always possible, also for adults managed by a parent before (P6)."""
    player, _ = await _subject(ctx, player_id)
    rows = (
        await ctx.db.scalars(
            select(Consent).where(
                Consent.player_id == player.id, Consent.kind == kind, Consent.revoked_at.is_(None)
            )
        )
    ).all()
    now = _now()
    for c in rows:
        c.revoked_at = now
    await audit.record(
        ctx,
        "consent.revoked_online",
        target_type="player",
        target_id=player.id,
        data={"kind": kind},
    )
    return len(rows)

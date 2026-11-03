"""Public player profile (addendum 01, 5.8).

Opt-in by the player (adults) or a parent (minors in adult teams); youth teams never have public
profiles (4.9). The profile needs an active `public_profile` consent, checked again on every
public read: revoking the consent or the profile takes it offline at once. Content: chosen highlight
reels of the player, position, shooting hand, chosen season figures and a short text. Not indexed by
search engines unless the person switches it on.
"""

from __future__ import annotations

import secrets
import unicodedata
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select

from handball_api.core.db import disable_system_access, enable_system_access, set_tenant
from handball_api.core.errors import ProblemError
from handball_api.models import (
    Event,
    Guardianship,
    HighlightReel,
    Match,
    Organization,
    Player,
    PublicProfile,
    RosterEntry,
    Team,
)
from handball_api.models.enums import ConsentKind, ReelStatus
from handball_api.schemas.profiles import ProfileIn
from handball_api.services import audit
from handball_api.services.context import Ctx
from handball_api.services.orgs import current_seasons
from handball_api.services.roster import consented

STATS = ("matches", "goals", "shots", "shooting_pct", "seven_m_goals", "assists", "saves")


async def _relation(ctx: Ctx, player_id: uuid.UUID) -> tuple[Player, str]:
    if ctx.user_id is None:
        raise ProblemError(401, "unauthenticated", "Sign in first")
    player = await ctx.db.get(Player, player_id)
    if player is None:
        raise ProblemError(404, "not-found", "Player not found")
    if player.user_id == ctx.user_id:
        return player, "self"
    guardian = await ctx.db.scalar(
        select(Guardianship.id).where(
            Guardianship.player_id == player.id, Guardianship.user_id == ctx.user_id
        )
    )
    if guardian:
        return player, "guardian"
    raise ProblemError(403, "forbidden", "Only the player or a parent manages the profile")


async def _team(ctx: Ctx, player: Player) -> Team | None:
    """The player's current team (latest roster entry)."""
    return await ctx.db.scalar(
        select(Team)
        .join(RosterEntry, RosterEntry.team_id == Team.id)
        .where(RosterEntry.player_id == player.id)
        .order_by(RosterEntry.created_at.desc())
        .limit(1)
    )


async def _eligibility(ctx: Ctx, player: Player) -> str | None:
    """None when the profile may be public, else the reason."""
    team = await _team(ctx, player)
    if team is None:
        return "no-team"
    if team.is_youth:
        return "youth-protection"
    if player.id not in await consented(ctx, [player.id], ConsentKind.PUBLIC_PROFILE):
        return "consent-missing"
    return None


def _slug(player: Player) -> str:
    base = unicodedata.normalize("NFKD", f"{player.first_name}-{player.last_name}")
    base = "".join(c for c in base if c.isascii() and (c.isalnum() or c == "-")).lower()
    return f"{base[:50].strip('-') or 'spieler'}-{secrets.token_hex(3)}"


async def _reels(ctx: Ctx, player: Player) -> list[HighlightReel]:
    return list(
        (
            await ctx.db.scalars(
                select(HighlightReel)
                .where(
                    HighlightReel.player_id == player.id, HighlightReel.status == ReelStatus.READY
                )
                .order_by(HighlightReel.created_at.desc())
            )
        ).all()
    )


async def mine(ctx: Ctx) -> list[dict[str, Any]]:
    """Profiles I can manage (myself, my children) with what can go on them."""
    if ctx.user_id is None:
        raise ProblemError(401, "unauthenticated", "Sign in first")
    own = (await ctx.db.scalars(select(Player).where(Player.user_id == ctx.user_id))).all()
    kids = (
        await ctx.db.scalars(
            select(Player)
            .join(Guardianship, Guardianship.player_id == Player.id)
            .where(Guardianship.user_id == ctx.user_id)
        )
    ).all()
    out = []
    for p, rel in [*((p, "self") for p in own), *((p, "guardian") for p in kids)]:
        profile = await ctx.db.scalar(select(PublicProfile).where(PublicProfile.player_id == p.id))
        out.append(
            {
                "player_id": p.id,
                "name": f"{p.first_name} {p.last_name}",
                "relation": rel,
                "blocked": await _eligibility(ctx, p),
                "profile": _profile_out(profile) if profile else None,
                "reels": [
                    {"id": r.id, "created_at": r.created_at, "format": r.format}
                    for r in await _reels(ctx, p)
                ],
                "stats_available": list(STATS),
            }
        )
    return out


def _profile_out(p: PublicProfile) -> dict[str, Any]:
    return {
        "slug": p.slug,
        "active": p.active,
        "views": p.views,
        "bio": p.content.get("bio"),
        "stats": p.content.get("stats") or [],
        "reel_ids": p.content.get("reel_ids") or [],
        "show_position": bool(p.content.get("show_position", True)),
        "show_hand": bool(p.content.get("show_hand", True)),
        "indexable": bool(p.content.get("indexable", False)),
    }


async def save(ctx: Ctx, player_id: uuid.UUID, data: ProfileIn) -> dict[str, Any]:
    player, _ = await _relation(ctx, player_id)
    if data.active:
        blocked = await _eligibility(ctx, player)
        if blocked == "youth-protection":
            raise ProblemError(403, "youth-protection", "No public profiles in youth teams")
        if blocked:
            raise ProblemError(403, "consent-missing", "The public profile needs the consent")
    reel_ids = {r.id for r in await _reels(ctx, player)}
    unknown = [r for r in data.reel_ids if r not in reel_ids]
    if unknown:
        raise ProblemError(422, "validation", "Only the player's own ready highlight reels")
    profile = await ctx.db.scalar(select(PublicProfile).where(PublicProfile.player_id == player.id))
    if profile is None:
        profile = PublicProfile(
            organization_id=player.organization_id, player_id=player.id, slug=_slug(player)
        )
        ctx.db.add(profile)
    profile.active = data.active
    profile.content = {
        "bio": data.bio,
        "stats": [s for s in data.stats if s in STATS],
        "reel_ids": [str(r) for r in data.reel_ids],
        "show_position": data.show_position,
        "show_hand": data.show_hand,
        "indexable": data.indexable,
    }
    profile.consent_checked_at = datetime.now(UTC)
    await ctx.db.flush()
    await audit.record(
        ctx,
        "profile.saved",
        target_type="player",
        target_id=player.id,
        data={"active": data.active},
    )
    return _profile_out(profile)


async def remove(ctx: Ctx, player_id: uuid.UUID) -> None:
    player, _ = await _relation(ctx, player_id)
    profile = await ctx.db.scalar(select(PublicProfile).where(PublicProfile.player_id == player.id))
    if profile is not None:
        await ctx.db.delete(profile)
        await audit.record(ctx, "profile.deleted", target_type="player", target_id=player.id)


async def _season_stats(ctx: Ctx, player: Player, team: Team) -> dict[str, float | int | None]:
    season = (await current_seasons(ctx, [team.id])).get(team.id)
    if season is None:
        return {}
    base = select(Event).join(Match, Match.id == Event.match_id).where(Match.season_id == season.id)
    own = base.where(Event.player_id == player.id)

    async def count(stmt: Any) -> int:
        return int(await ctx.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)

    shots = await count(own.where(Event.type == "shot"))
    goals = await count(own.where(Event.type == "shot", Event.outcome == "goal"))
    return {
        "matches": int(
            await ctx.db.scalar(
                select(func.count(func.distinct(Event.match_id)))
                .join(Match, Match.id == Event.match_id)
                .where(Match.season_id == season.id, Event.player_id == player.id)
            )
            or 0
        ),
        "goals": goals,
        "shots": shots,
        "shooting_pct": round(goals / shots, 3) if shots else None,
        "seven_m_goals": await count(
            own.where(Event.type == "shot", Event.outcome == "goal", Event.shot_type == "penalty")
        ),
        "assists": await count(base.where(Event.assist_player_id == player.id)),
        "saves": await count(
            base.where(
                Event.type == "shot",
                Event.outcome == "save",
                Event.attributes["goalkeeper_id"].astext == str(player.id),
            )
        ),
    }


async def _public(ctx: Ctx, slug: str) -> tuple[PublicProfile, Player, Team]:
    await enable_system_access(ctx.db, reason="public profile lookup")
    profile = await ctx.db.scalar(select(PublicProfile).where(PublicProfile.slug == slug))
    await disable_system_access(ctx.db)
    if profile is None or not profile.active:
        raise ProblemError(404, "not-found", "This profile is not public")
    await set_tenant(ctx.db, profile.organization_id)
    player = await ctx.db.get(Player, profile.player_id)
    team = await _team(ctx, player) if player else None
    if player is None or team is None or await _eligibility(ctx, player):
        # consent revoked or team now youth: offline immediately
        raise ProblemError(404, "not-found", "This profile is not public")
    return profile, player, team


async def public(ctx: Ctx, slug: str) -> dict[str, Any]:
    profile, player, team = await _public(ctx, slug)
    profile.views += 1
    c = profile.content
    stats = await _season_stats(ctx, player, team)
    org = await ctx.db.get(Organization, team.organization_id)
    return {
        "name": f"{player.first_name} {player.last_name}",
        "club": org.name if org else "",
        "team": team.name,
        "position": player.main_position if c.get("show_position", True) else None,
        "shooting_hand": player.shooting_hand if c.get("show_hand", True) else None,
        "bio": c.get("bio"),
        "stats": {k: stats.get(k) for k in c.get("stats") or [] if k in stats},
        "reels": c.get("reel_ids") or [],
        "indexable": bool(c.get("indexable", False)),
    }


async def public_reel(ctx: Ctx, slug: str, reel_id: uuid.UUID) -> bytes:
    profile, player, _ = await _public(ctx, slug)
    if str(reel_id) not in (profile.content.get("reel_ids") or []):
        raise ProblemError(404, "not-found", "Not found")
    reel = await ctx.db.get(HighlightReel, reel_id)
    if (
        reel is None
        or reel.player_id != player.id
        or reel.status != ReelStatus.READY
        or not reel.output_key
    ):
        raise ProblemError(404, "not-found", "Not found")
    data, _ = await ctx.storage.get(ctx.settings.s3_bucket_artifacts, reel.output_key)
    return data

"""Clubs and teams from the official league data, Switzerland first (handball.ch).

docs/plans/federation-onboarding.md, phases 1 and 3:
- search: club name or town, the hits are the registered teams of the current season;
- claim: creates or links the organisation (one per official club) and the team with the
  official ids and prefills the season schedule with results, the standing, roster suggestions
  (name, shirt number, appearances and the official statistics the coach may show; the coach
  confirms) and the past games with a game log as importable reports. Official games count toward
  the plan's matches per season: over the limit they stay suggestions (reason plan_limit).
  Someone claiming a club or team that is already in the app asks its admins for access instead
  (org_access_requests);
- sync: daily (worker tick) and on demand. Moved and new games, roster changes and the next
  season come in as suggestions; results are taken over; after each game the official report is
  imported automatically.

Data protection: names from the official data are only suggestions for the team's organisers;
an accepted roster entry from the official data stays hidden from the other team members until
the person joins or a consent is recorded (services/roster.py). No public profiles from it.

The module is a package: `claim` (search and claim), `sync`, `suggestions`, `access` (access
requests) and the worker tick here. The tick stays in this module so that it calls `sync_team`,
`import_report` and reads `REPORT_BATCH` through this namespace (tests replace them here); all
names callers use are importable from `services.official`.
"""

from __future__ import annotations

import uuid
from collections import Counter
from datetime import datetime, timedelta

from sqlalchemy import select, update

from handball_api.core.db import disable_system_access, enable_system_access, set_tenant
from handball_api.core.errors import ProblemError
from handball_api.integrations import handball_ch as ch
from handball_api.models import Match, Membership, Team
from handball_api.models.enums import OrgRole, TeamRole
from handball_api.services import training
from handball_api.services.context import Ctx
from handball_api.services.official._base import (
    MAX_CLUBS,
    MIN_QUERY,
    PLAN_LIMIT,
    PROVIDER,
    REPORT_AFTER,
    REPORT_BACKFILL_TRIES,
    REPORT_BATCH,
    REPORT_RETRY,
    REPORT_RETRY_MAX,
    REPORT_WINDOW,
    ROSTER_STATS,
    STATS_GAMES,
    SYNC_BATCH,
    SYNC_EVERY,
    SYSTEM_USER,
    _now,
    _unavailable,
    log,
)
from handball_api.services.official.access import (
    _access_request,
    approve_access,
    decline_access,
    list_access_requests,
    my_access_requests,
)
from handball_api.services.official.claim import (
    _create_team,
    _official_team,
    _request_access,
    _tokens,
    claim,
    gender_of,
    is_youth,
    search,
)
from handball_api.services.official.suggestions import (
    _out,
    _played_match,
    _resolve,
    _start_season,
    _suggestion,
    _team_season,
    accept,
    add_from_suggestion,
    dismiss,
    import_report,
    list_suggestions,
    number_free,
)
from handball_api.services.official.sync import (
    _add,
    _game_payload,
    _held_back,
    _new_match,
    _next_season,
    _opponent,
    _opponents,
    _roster,
    _scores,
    _season_row,
    _split_name,
    _Stats,
    _Suggester,
    _suggestions,
    link,
    set_preferences,
    sync_now,
    sync_team,
)
from handball_api.services.policies import Actor

__all__ = [
    "MAX_CLUBS",
    "MIN_QUERY",
    "PLAN_LIMIT",
    "PROVIDER",
    "REPORT_AFTER",
    "REPORT_BACKFILL_TRIES",
    "REPORT_BATCH",
    "REPORT_RETRY",
    "REPORT_RETRY_MAX",
    "REPORT_WINDOW",
    "ROSTER_STATS",
    "STATS_GAMES",
    "SYNC_BATCH",
    "SYNC_EVERY",
    "SYSTEM_USER",
    "_Stats",
    "_Suggester",
    "_access_request",
    "_add",
    "_create_team",
    "_game_payload",
    "_held_back",
    "_import_due_report",
    "_new_match",
    "_next_season",
    "_now",
    "_official_team",
    "_opponent",
    "_opponents",
    "_organisers",
    "_out",
    "_played_match",
    "_postpone_report",
    "_postpone_team",
    "_request_access",
    "_resolve",
    "_retry_after",
    "_roster",
    "_scores",
    "_season_row",
    "_split_name",
    "_start_season",
    "_suggestion",
    "_suggestions",
    "_sync_due_team",
    "_system_actor",
    "_team_season",
    "_tokens",
    "_unavailable",
    "_upstream_down",
    "accept",
    "add_from_suggestion",
    "approve_access",
    "claim",
    "decline_access",
    "dismiss",
    "gender_of",
    "import_report",
    "is_youth",
    "link",
    "list_access_requests",
    "list_suggestions",
    "log",
    "my_access_requests",
    "number_free",
    "run_due",
    "search",
    "set_preferences",
    "sync_now",
    "sync_team",
]


# ---- worker tick -------------------------------------------------------------------------------


def _system_actor(org_id: uuid.UUID) -> Actor:
    return Actor(user_id=SYSTEM_USER, organization_id=org_id, org_role=OrgRole.ORG_ADMIN)


async def _organisers(ctx: Ctx, team_id: uuid.UUID) -> list[uuid.UUID]:
    rows = await ctx.db.scalars(
        select(Membership.user_id).where(
            Membership.team_id == team_id,
            Membership.role.in_([TeamRole.COACH, TeamRole.TEAM_MANAGER]),
        )
    )
    return list(rows.all())


def _retry_after(tries: int) -> timedelta:
    """Wait after the n-th tick without a game log: an hour, then doubling up to a day."""
    wait: timedelta = REPORT_RETRY * 2 ** min(max(tries - 1, 0), 10)
    return min(wait, REPORT_RETRY_MAX)


async def _sync_due_team(ctx: Ctx, team: Team) -> int:
    counts = await sync_team(ctx, team)
    new = counts["roster_suggestions"] + counts["other_suggestions"]
    if new:
        await training.notify(
            ctx,
            team.organization_id,
            await _organisers(ctx, team.id),
            "official_suggestions",
            # the note names the team (app review UX-10): a club with several teams knows which
            {"team_id": str(team.id), "team": team.name, "count": new},
            f"/app/{team.organization_id}/teams/{team.id}/official",
        )
    return new


async def _import_due_report(ctx: Ctx, m: Match, now: datetime) -> None:
    await import_report(ctx, m)
    if m.kickoff_at < now - REPORT_WINDOW:
        return  # an earlier game filled in: no note for each of them in the bell (R5)
    await training.notify(
        ctx,
        m.organization_id,
        await training.staff_of(ctx, m.team_id),
        "official_report",
        {"match_id": str(m.id)},
        f"/app/{m.organization_id}/matches/{m.id}",
    )


def _upstream_down(exc: ProblemError) -> bool:
    return exc.code in ("official-unavailable", "report-unavailable")


async def run_due(ctx: Ctx, now: datetime | None = None) -> dict[str, int]:
    """Hourly worker tick: each linked team once a day (schedule, roster, standing, next season
    as suggestions) and the official report of every linked game that ended, the latest first;
    cached handball.ch answers past their retention are deleted.

    Each team and each game runs in its own savepoint: an unexpected error rolls back that team
    (tried again the next day) or game (tried again later), not the whole tick. A game without a
    game log yet is asked again after an hour, then after ever longer waits (up to a day). Stops
    at the first sign that handball.ch is not answering (no hammering)."""
    now = now or _now()
    out = Counter[str]()
    # public answers of handball.ch (no tenant data): kept only as long as they are useful
    out["purged"] = await ch.purge_cache(ctx.db, now)
    await enable_system_access(ctx.db, reason="official data sync")
    try:
        teams = [
            (t.id, t.organization_id)
            for t in await ctx.db.execute(
                select(Team.id, Team.organization_id)
                .where(
                    Team.official_team_id.is_not(None),
                    (Team.official_synced_at.is_(None))
                    | (Team.official_synced_at < now - SYNC_EVERY),
                )
                .order_by(Team.official_synced_at.nulls_first())
                .limit(SYNC_BATCH)
            )
        ]
        games = [
            (g.id, g.organization_id)
            for g in await ctx.db.execute(
                select(Match.id, Match.organization_id)
                .where(
                    Match.official_game_id.is_not(None),
                    Match.official_report_at.is_(None),
                    Match.kickoff_at < now - REPORT_AFTER,
                    (Match.kickoff_at > now - REPORT_WINDOW)
                    | (Match.official_report_tries < REPORT_BACKFILL_TRIES),
                    Match.official_report_retry_at.is_(None)
                    | (Match.official_report_retry_at <= now),
                )
                .order_by(Match.kickoff_at.desc())
                .limit(REPORT_BATCH)
            )
        ]
    finally:
        await disable_system_access(ctx.db)
    try:
        for team_id, org_id in teams:
            await set_tenant(ctx.db, org_id)
            ctx.actor = _system_actor(org_id)
            try:
                async with ctx.db.begin_nested():
                    team = await ctx.db.get(Team, team_id)
                    if team is None:
                        continue
                    new = await _sync_due_team(ctx, team)
                out["teams"] += 1
                out["suggestions"] += new
            except ProblemError as exc:
                if _upstream_down(exc):
                    raise
                log.warning("official_sync_failed", team_id=str(team_id), error=exc.code)
                out["failed"] += 1
                await _postpone_team(ctx, team_id, now)
            except Exception:
                log.exception("official_sync_failed", team_id=str(team_id))
                out["failed"] += 1
                await _postpone_team(ctx, team_id, now)
        for match_id, org_id in games:
            await set_tenant(ctx.db, org_id)
            ctx.actor = _system_actor(org_id)
            try:
                async with ctx.db.begin_nested():
                    m = await ctx.db.get(Match, match_id)
                    if m is None:
                        continue
                    await _import_due_report(ctx, m, now)
                out["reports"] += 1
            except ProblemError as exc:
                if _upstream_down(exc):
                    raise
                if exc.code != "report-empty":  # no game log yet: asked again later
                    log.warning("official_report_failed", match_id=str(match_id), error=exc.code)
                    out["failed"] += 1
                await _postpone_report(ctx, match_id, now)
            except Exception:
                log.exception("official_report_failed", match_id=str(match_id))
                out["failed"] += 1
                await _postpone_report(ctx, match_id, now)
    except ProblemError as exc:
        if not _upstream_down(exc):
            raise
        out["stopped"] = 1
    finally:
        ctx.actor = None
    await ctx.db.flush()
    keys = ("teams", "suggestions", "reports", "failed", "stopped", "purged")
    return {k: out[k] for k in keys}


async def _postpone_team(ctx: Ctx, team_id: uuid.UUID, now: datetime) -> None:
    """A team whose sync failed is tried again with the next day's sync, not every hour."""
    await ctx.db.execute(
        update(Team)
        .where(Team.id == team_id)
        .values(official_synced_at=now)
        .execution_options(synchronize_session=False)
    )


async def _postpone_report(ctx: Ctx, match_id: uuid.UUID, now: datetime) -> None:
    tries = (
        await ctx.db.scalar(select(Match.official_report_tries).where(Match.id == match_id)) or 0
    ) + 1
    await ctx.db.execute(
        update(Match)
        .where(Match.id == match_id)
        .values(official_report_tries=tries, official_report_retry_at=now + _retry_after(tries))
        .execution_options(synchronize_session=False)
    )

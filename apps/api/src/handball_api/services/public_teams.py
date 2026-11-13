"""The public entry (UX test, second delivery): find your team and see it before an account.

Reads only what the federation publishes (handball.ch cache): team and club names, league, the
table, results, the next game and the scorers of the played games. Nothing of the app's own data
is shown except whether a team is already in the app (so saving asks the club instead).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from handball_api.core.db import disable_system_access, enable_system_access
from handball_api.core.errors import ProblemError
from handball_api.integrations import handball_ch as ch
from handball_api.models import Team
from handball_api.services.context import Ctx
from handball_api.services.official import (
    MAX_CLUBS,
    MIN_QUERY,
    PROVIDER,
    _official_team,
    _tokens,
    _unavailable,
)

SCORER_GAMES = 12  # the scorers from at most the last twelve played games (one request each)


async def search(ctx: Ctx, q: str) -> list[dict[str, Any]]:
    """Teams of the current season of clubs matching the name or town, without the app's ids."""
    tokens = _tokens(q)
    if len("".join(tokens)) < MIN_QUERY:
        raise ProblemError(422, "query-too-short", "Type at least three letters")
    try:
        season = await ch.current_season(ctx.db)
        found = []
        for c in await ch.clubs(ctx.db):
            text = ch.fold(f"{c.name} {c.city or ''}")
            if all(t in text for t in tokens):
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
                        "group_name": t.group_name,
                        "club": {"id": c.id, "name": c.name, "city": c.city},
                        "in_app": False,
                    }
                )
    except ch.UpstreamUnavailableError as exc:
        raise _unavailable(exc) from exc
    if hits:
        await enable_system_access(ctx.db, reason="public team search: which teams are in the app")
        try:
            linked = set(
                (
                    await ctx.db.scalars(
                        select(Team.official_team_id).where(
                            Team.official_provider == PROVIDER,
                            Team.official_team_id.in_([h["official_id"] for h in hits]),
                        )
                    )
                ).all()
            )
        finally:
            await disable_system_access(ctx.db)
        for h in hits:
            h["in_app"] = h["official_id"] in linked
    return hits


def _result(own: int | None, opp: int | None) -> str | None:
    if own is None or opp is None:
        return None
    return "w" if own > opp else "l" if own < opp else "d"


async def preview(ctx: Ctx, club_id: int, official_id: int) -> dict[str, Any]:
    """The team as the federation shows it: last result, rank and table, the form, the scorers,
    the next game."""
    season, detail, team = await _official_team(ctx, club_id, official_id)
    try:
        games = await ch.team_games(ctx.db, team.id)
        table = await ch.standing(ctx.db, team.group_id) if team.group_id else []
    except ch.UpstreamUnavailableError as exc:
        raise _unavailable(exc) from exc
    now = datetime.now(UTC)

    def side(g: ch.OfficialGame) -> dict[str, Any]:
        home = g.home_team_id == team.id
        return {
            "opponent": g.away_name if home else g.home_name,
            "home": home,
            "own": g.home_score if home else g.away_score,
            "opp": g.away_score if home else g.home_score,
            "half_own": g.home_half if home else g.away_half,
            "half_opp": g.away_half if home else g.home_half,
            "kickoff_at": g.kickoff_at,
            "venue": g.venue,
        }

    played = [g for g in games if g.played and g.home_score is not None]
    upcoming = [g for g in games if not g.played and g.kickoff_at > now]
    form = [r for g in played if (r := _result(side(g)["own"], side(g)["opp"]))]
    run = 0
    for r in reversed(form):
        if r != form[-1]:
            break
        run += 1
    # the scorers of the team from the federation's player statistics of the played games
    goals: dict[int, int] = defaultdict(int)
    names: dict[int, str] = {}
    counted = 0
    try:
        for g in played[-SCORER_GAMES:]:
            for p in await ch.game_players(ctx.db, g.id):
                if p.team_id == team.id and p.goals:
                    goals[p.player_id] += p.goals
                    names[p.player_id] = p.name or ""
            counted += 1
    except ch.UpstreamUnavailableError:
        pass  # the preview stands without scorers
    scorers = [
        {"name": names[pid], "goals": n}
        for pid, n in sorted(goals.items(), key=lambda kv: -kv[1])[:5]
        if names[pid]
    ]
    rank = next((r.get("rank") for r in table if r.get("teamId") == team.id), None)
    return {
        "official_id": team.id,
        "name": team.name,
        "club": {"id": detail.id, "name": detail.name, "city": detail.city},
        "league": team.league,
        "group_name": team.group_name,
        "season": season.label,
        "last": side(played[-1]) if played else None,
        "next": side(upcoming[0]) if upcoming else None,
        "rank": rank,
        "table": [
            {
                "rank": r.get("rank"),
                "name": r.get("name"),
                "games": r.get("games"),
                "points": r.get("points"),
                "goal_difference": r.get("goalDifference"),
                "own": r.get("teamId") == team.id,
            }
            for r in table
        ],
        "form": form[-5:],
        "run": {"result": form[-1], "count": run} if form else None,
        "played": len(played),
        "scorers": scorers,
        "scorer_games": counted,
    }

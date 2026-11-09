"""A team's analysable events in the form of `handball_metrics.query` (M10: assistant 5.1,
statistics matrix 5.4). The caller checks the permission for the team before loading."""

from __future__ import annotations

import uuid
from collections.abc import Collection
from dataclasses import replace
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import load_only

from handball_api.models import (
    Event,
    Match,
    Opponent,
    Play,
    Player,
    RosterEntry,
    Season,
    Team,
)
from handball_api.services.context import Ctx
from handball_api.services.events import _to_metric
from handball_api.services.matches import (
    duration_ms,
    in_video,
    timeline_videos,
    video_formations,
)
from handball_metrics.model import Event as MEvent
from handball_metrics.query import MatchInfo, Row

# what _to_metric and load read of an event (not its free text columns, timestamps, ...)
EVENT_COLUMNS = (
    *(Event.id, Event.match_id, Event.type, Event.side, Event.period, Event.clock_s, Event.t_ms),
    *(Event.player_id, Event.number, Event.x, Event.y, Event.outcome, Event.shot_zone),
    *(Event.goal_zone, Event.shot_type, Event.turnover_type, Event.assist_player_id),
    *(Event.confidence, Event.source, Event.attributes),
)


class TeamData:
    """The analysable events of one team (matches only, no trainings)."""

    def __init__(
        self,
        team: Team,
        matches: list[MatchInfo],
        rows: list[Row],
        video: dict[str, int | None],
        plays: dict[str, str],
    ) -> None:
        self.team = team
        self.matches = {m.id: m for m in matches}
        self.rows = rows
        self.event_ms = video  # event id -> video time (None without video)
        self.by_id = {r.event.id: r for r in rows}
        self.plays = plays  # play id -> name


async def season_scope(
    ctx: Ctx,
    team: Team,
    season_ids: Collection[uuid.UUID] | None = None,
    since: date | None = None,
) -> list[uuid.UUID]:
    """The team's seasons to read: the ones asked for, else every season that ends on or after
    `since` (default: the start of the current season) and the one before it (for a comparison
    with the last matches before). Without seasons nothing is read."""
    seasons = (
        await ctx.db.execute(
            select(Season.id, Season.starts_on, Season.ends_on)
            .where(Season.team_id == team.id)
            .order_by(Season.starts_on.desc())
        )
    ).all()
    if season_ids is not None:
        wanted = set(season_ids)
        return [sid for sid, _, _ in seasons if sid in wanted]
    if since is None:
        today = datetime.now(UTC).date()
        current = next((s for s in seasons if s.starts_on <= today <= s.ends_on), None)
        if current is None:  # between seasons: the latest that started
            current = next((s for s in seasons if s.starts_on <= today), None)
        if current is None:
            return [sid for sid, _, _ in seasons]  # only future seasons
        since = current.starts_on
    recent = [sid for sid, _, ends_on in seasons if ends_on >= since]
    older = [sid for sid, _, ends_on in seasons if ends_on < since]
    return recent + older[:1]


async def load(
    ctx: Ctx,
    team: Team,
    season_ids: Collection[uuid.UUID] | None = None,
    since: date | None = None,
) -> TeamData:
    """The events of the team's matches in the seasons of `season_scope` (by default the
    current and the previous season), with only the columns the statistics use."""
    scope = await season_scope(ctx, team, season_ids, since)
    matches = (
        (
            await ctx.db.execute(
                select(
                    Match.id,
                    Match.season_id,
                    Match.kickoff_at,
                    Match.opponent_id,
                    Match.score_own,
                    Match.score_opponent,
                    Match.kind,
                ).where(
                    Match.team_id == team.id,
                    Match.kind == "match",
                    Match.season_id.in_(scope),
                )
            )
        ).all()
        if scope
        else []
    )
    ids = [m.id for m in matches]
    opponent_ids = {m.opponent_id for m in matches if m.opponent_id}
    opponents: dict[uuid.UUID, str] = (
        dict(
            (
                await ctx.db.execute(
                    select(Opponent.id, Opponent.name).where(Opponent.id.in_(opponent_ids))
                )
            )
            .tuples()
            .all()
        )
        if opponent_ids
        else {}
    )
    entries = (
        (
            await ctx.db.execute(
                select(
                    RosterEntry.season_id, RosterEntry.player_id, RosterEntry.jersey_number
                ).where(RosterEntry.team_id == team.id, RosterEntry.season_id.in_(scope))
            )
        ).all()
        if scope
        else []
    )
    numbers = {(r.season_id, r.player_id): r.jersey_number for r in entries}
    player_ids = {r.player_id for r in entries}
    positions = (
        {
            pid: (pos.value if pos else None)
            for pid, pos in (
                await ctx.db.execute(
                    select(Player.id, Player.main_position).where(Player.id.in_(player_ids))
                )
            )
            .tuples()
            .all()
        }
        if player_ids
        else {}
    )
    plays = {
        str(pid): name
        for pid, name in (
            await ctx.db.execute(select(Play.id, Play.name).where(Play.team_id == team.id))
        )
        .tuples()
        .all()
    }
    timeline = await timeline_videos(ctx, ids, ready=False)
    found = await video_formations(ctx, [v.id for v in timeline.values()])
    formations: dict[uuid.UUID, tuple[tuple[int, int, str], ...]] = {}
    for v in timeline.values():
        segs = [
            (int(s["start_ms"]), int(s["end_ms"]), str(s["formation"]))
            for s in found.get(v.id, [])
            if s.get("team") == "away"
        ]
        if segs:
            formations[v.match_id] = tuple(segs)
    infos = {
        m.id: MatchInfo(
            id=str(m.id),
            date=m.kickoff_at.date().isoformat(),
            opponent=opponents.get(m.opponent_id) if m.opponent_id else None,
            score_own=m.score_own,
            score_opponent=m.score_opponent,
            kind=m.kind,
            opponent_formations=formations.get(m.id, ()),
        )
        for m in matches
    }
    season = {m.id: m.season_id for m in matches}
    rows: list[Row] = []
    video: dict[str, int | None] = {}
    events = (
        (
            await ctx.db.scalars(
                select(Event).options(load_only(*EVENT_COLUMNS)).where(Event.match_id.in_(ids))
            )
        ).all()
        if ids
        else []
    )
    for e in events:
        me = _to_metric(e)
        if e.side == "own" and e.player_id is not None:
            # own players are identified by their jersey number of that season; the position is
            # a grouping of the statistics matrix; the person's id stays inside the API
            num = (
                me.number
                if me.number is not None
                else numbers.get((season[e.match_id], e.player_id))
            )
            attrs = {**me.attributes, "position": positions.get(e.player_id)}
            me = _anonymous(me, num, attrs)
        rows.append(Row(me, infos[e.match_id]))
        # a clip only for a moment the video shows (official report events of a clip from
        # mid-half lie before or after it)
        length = duration_ms(timeline.get(e.match_id))
        video[str(e.id)] = e.t_ms if in_video(e.t_ms, length) else None
    return TeamData(team, list(infos.values()), rows, video, plays)


def _anonymous(e: MEvent, number: int | None, attributes: dict[str, object]) -> MEvent:
    return replace(e, number=number, player_id=None, assist_player_id=None, attributes=attributes)

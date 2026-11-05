"""A team's analysable events in the form of `handball_metrics.query` (M10: assistant 5.1,
statistics matrix 5.4). The caller checks the permission for the team before loading."""

from __future__ import annotations

import uuid
from dataclasses import replace

from sqlalchemy import select

from handball_api.models import (
    Event,
    Match,
    Opponent,
    Play,
    Player,
    RosterEntry,
    Team,
)
from handball_api.services.context import Ctx
from handball_api.services.events import _to_metric
from handball_api.services.matches import duration_ms, in_video, timeline_videos
from handball_metrics.model import Event as MEvent
from handball_metrics.query import MatchInfo, Row


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


async def load(ctx: Ctx, team: Team) -> TeamData:
    matches = (
        await ctx.db.scalars(select(Match).where(Match.team_id == team.id, Match.kind == "match"))
    ).all()
    ids = [m.id for m in matches]
    opponents = {
        o.id: o.name
        for o in (
            await ctx.db.scalars(
                select(Opponent).where(
                    Opponent.id.in_([m.opponent_id for m in matches if m.opponent_id])
                )
            )
        ).all()
    }
    entries = (
        await ctx.db.scalars(select(RosterEntry).where(RosterEntry.team_id == team.id))
    ).all()
    numbers = {(r.season_id, r.player_id): r.jersey_number for r in entries}
    positions = {
        p.id: (p.main_position.value if p.main_position else None)
        for p in (
            await ctx.db.scalars(
                select(Player).where(Player.id.in_({r.player_id for r in entries}))
            )
        ).all()
    }
    plays = {
        str(p.id): p.name
        for p in (await ctx.db.scalars(select(Play).where(Play.team_id == team.id))).all()
    }
    formations: dict[uuid.UUID, tuple[tuple[int, int, str], ...]] = {}
    timeline = await timeline_videos(ctx, ids, ready=False)
    for v in timeline.values():
        segs = [
            (int(s["start_ms"]), int(s["end_ms"]), str(s["formation"]))
            for s in (v.analysis or {}).get("formations") or []
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
        (await ctx.db.scalars(select(Event).where(Event.match_id.in_(ids)))).all() if ids else []
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

"""Events, corrections, statistics and official feed import (BRIEF 4.5, 4.8, 7.4)."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError

from handball_api.core.errors import ProblemError
from handball_api.models import (
    Correction,
    Event,
    Match,
    Possession,
    RosterEntry,
    StatsCache,
    VideoAsset,
)
from handball_api.models.enums import VideoRole
from handball_api.schemas.events import EventIn, EventPatch
from handball_api.services import audit
from handball_api.services.context import Ctx
from handball_api.services.matches import get_match
from handball_api.services.policies import Action
from handball_court.zones import shot_zone
from handball_metrics import Event as MEvent
from handball_metrics import EventType as MEventType
from handball_metrics import Side as MSide
from handball_metrics import compute_match_stats
from handball_metrics.stats import METRICS_VERSION

EVENT_FIELDS = (
    "type",
    "side",
    "period",
    "clock_s",
    "t_ms",
    "player_id",
    "number",
    "x",
    "y",
    "outcome",
    "shot_zone",
    "goal_zone",
    "shot_type",
    "turnover_type",
    "assist_player_id",
    "source",
    "confidence",
)


def _snapshot(e: Event) -> dict[str, Any]:
    return {
        k: (str(v) if isinstance(v, uuid.UUID) else v)
        for k, v in ((f, getattr(e, f)) for f in EVENT_FIELDS)
    }


def clock_from_video(match: Match, t_ms: int) -> tuple[int, float] | None:
    """(period, match clock in s) for a video time, using the stored throw-off times per half."""
    k = match.kickoff_ms or {}
    starts = sorted((int(p), ms) for p, ms in k.items() if ms <= t_ms)
    if not starts:
        return None
    period, start = starts[-1]
    return period, round((period - 1) * match.period_s + (t_ms - start) / 1000, 1)


def video_from_clock(match: Match, period: int, clock_s: float) -> int | None:
    k = match.kickoff_ms or {}
    start = k.get(str(period))
    if start is None:
        return None
    return int(start + (clock_s - (period - 1) * match.period_s) * 1000)


def _zone(data: EventIn | Event) -> str | None:
    if data.type != "shot":
        return None
    if data.shot_type in ("penalty", "fast_break"):
        return "penalty" if data.shot_type == "penalty" else "fast_break"
    if data.x is not None and data.y is not None:
        return shot_zone(data.x, data.y)
    return None


async def _check_players(ctx: Ctx, match: Match, *ids: uuid.UUID | None) -> None:
    wanted = {i for i in ids if i}
    if not wanted:
        return
    found = set(
        (
            await ctx.db.scalars(
                select(RosterEntry.player_id).where(
                    RosterEntry.team_id == match.team_id, RosterEntry.player_id.in_(wanted)
                )
            )
        ).all()
    )
    if wanted - found:
        raise ProblemError(422, "player-not-in-team", "Player is not in this team's roster")


async def create_event(
    ctx: Ctx, match_id: uuid.UUID, data: EventIn, source: str = "user_correction"
) -> Event:
    match = await get_match(ctx, match_id, Action.EVENT_WRITE)
    if data.client_id is not None:
        existing = await ctx.db.scalar(
            select(Event).where(Event.match_id == match.id, Event.client_id == data.client_id)
        )
        if existing is not None:
            return existing
    await _check_players(ctx, match, data.player_id, data.assist_player_id)
    values = data.model_dump()
    if data.t_ms is not None and data.clock_s is None:
        derived = clock_from_video(match, data.t_ms)
        if derived:
            values["period"], values["clock_s"] = derived
    if data.t_ms is None and data.clock_s is not None:
        values["t_ms"] = video_from_clock(match, data.period, data.clock_s)
    ev = Event(
        organization_id=match.organization_id,
        match_id=match.id,
        source=source,
        confidence=1.0,
        shot_zone=_zone(data),
        created_by_id=ctx.user_id,
        **values,
    )
    try:
        async with ctx.db.begin_nested():
            ctx.db.add(ev)
            await ctx.db.flush()
    except IntegrityError:
        # the same offline event arrived twice at the same moment: return the stored one
        existing = await ctx.db.scalar(
            select(Event).where(Event.match_id == match.id, Event.client_id == data.client_id)
        )
        if existing is None:
            raise
        return existing
    ctx.db.add(
        Correction(
            organization_id=match.organization_id,
            match_id=match.id,
            event_id=ev.id,
            action="create",
            after=_snapshot(ev),
            user_id=ctx.user_id,
        )
    )
    return ev


async def _event(ctx: Ctx, event_id: uuid.UUID) -> tuple[Event, Match]:
    ev = await ctx.db.get(Event, event_id)
    if ev is None:
        raise ProblemError(404, "not-found", "Event not found")
    match = await get_match(ctx, ev.match_id, Action.EVENT_WRITE)
    return ev, match


async def update_event(ctx: Ctx, event_id: uuid.UUID, data: EventPatch) -> Event:
    ev, match = await _event(ctx, event_id)
    before = _snapshot(ev)
    values = data.model_dump(exclude_unset=True)
    await _check_players(ctx, match, values.get("player_id"), values.get("assist_player_id"))
    for k, v in values.items():
        setattr(ev, k, v)
    if ev.type != "shot" and (ev.outcome or ev.goal_zone):
        raise ProblemError(422, "invalid-event", "outcome and goal zone only apply to shots")
    ev.shot_zone = _zone(ev)
    ev.source, ev.confidence = "user_correction", 1.0  # a person confirmed it
    ctx.db.add(
        Correction(
            organization_id=match.organization_id,
            match_id=match.id,
            event_id=ev.id,
            action="update",
            before=before,
            after=_snapshot(ev),
            user_id=ctx.user_id,
        )
    )
    return ev


async def delete_event(ctx: Ctx, event_id: uuid.UUID) -> None:
    ev, match = await _event(ctx, event_id)
    ctx.db.add(
        Correction(
            organization_id=match.organization_id,
            match_id=match.id,
            event_id=ev.id,
            action="delete",
            before=_snapshot(ev),
            user_id=ctx.user_id,
        )
    )
    await ctx.db.delete(ev)


async def list_events(
    ctx: Ctx,
    match_id: uuid.UUID,
    *,
    side: str | None = None,
    type_: str | None = None,
    outcome: str | None = None,
    player_id: uuid.UUID | None = None,
    number: int | None = None,
    zone: str | None = None,
    goal_zone: str | None = None,
    turnover_type: str | None = None,
) -> list[Event]:
    await get_match(ctx, match_id)
    q = select(Event).where(Event.match_id == match_id)
    for col, val in (
        (Event.side, side),
        (Event.type, type_),
        (Event.outcome, outcome),
        (Event.player_id, player_id),
        (Event.number, number),
        (Event.shot_zone, zone),
        (Event.goal_zone, goal_zone),
        (Event.turnover_type, turnover_type),
    ):
        if val is not None:
            q = q.where(col == val)
    q = q.order_by(
        Event.period, Event.clock_s.nulls_last(), Event.t_ms.nulls_last(), Event.created_at
    )
    return list((await ctx.db.scalars(q)).all())


def _to_metric(e: Event) -> MEvent:
    try:
        etype = MEventType(e.type)
    except ValueError:
        etype = MEventType.FOUL
    return MEvent(
        id=str(e.id),
        type=etype,
        side=MSide(e.side),
        period=e.period,
        clock_s=e.clock_s,
        t_ms=e.t_ms,
        player_id=str(e.player_id) if e.player_id else None,
        number=e.number,
        x=e.x,
        y=e.y,
        outcome=e.outcome,
        shot_zone=e.shot_zone,
        goal_zone=e.goal_zone,
        shot_type=e.shot_type,
        turnover_type=e.turnover_type,
        assist_player_id=str(e.assist_player_id) if e.assist_player_id else None,
        confidence=e.confidence,
        source=e.source,
        attributes=e.attributes or {},
    )


def estimate_possessions(events: list[MEvent]) -> dict[str, int]:
    """Possessions estimate when tracking-based possessions are missing (source heuristic):
    shots that end the attack (not blocked) + turnovers, per team."""
    out = {"own": 0, "opponent": 0}
    for e in events:
        if (e.is_shot and e.outcome != "blocked") or e.type is MEventType.TURNOVER:
            out[e.side.value] += 1
    return out


async def match_stats(ctx: Ctx, match_id: uuid.UUID) -> dict[str, Any]:
    return await stats_for(ctx, await get_match(ctx, match_id))


async def stats_for(ctx: Ctx, match: Match) -> dict[str, Any]:
    """Stats of a match the caller has already been authorised for (cached by event version)."""
    count, latest = (
        await ctx.db.execute(
            select(func.count(Event.id), func.max(Event.updated_at)).where(
                Event.match_id == match.id
            )
        )
    ).one()
    tracked = dict(
        (
            await ctx.db.execute(
                select(Possession.side, func.count(Possession.id))
                .where(Possession.match_id == match.id)
                .group_by(Possession.side)
            )
        ).all()
    )
    version = hashlib.sha256(
        f"{count}|{latest}|{sorted(tracked.items())}|{METRICS_VERSION}".encode()
    ).hexdigest()[:32]
    cached = await cache_get(ctx, "match", match.id, version)
    if cached is not None:
        return cached
    events = [
        _to_metric(e)
        for e in (await ctx.db.scalars(select(Event).where(Event.match_id == match.id))).all()
    ]
    if tracked:
        # possession phases from the tracking (A3) instead of the estimate from events
        possessions = {"own": tracked.get("own", 0), "opponent": tracked.get("opponent", 0)}
        source = "tracking"
    else:
        possessions = estimate_possessions(events)
        source = "heuristic_estimate"
    data = compute_match_stats(events, possessions)
    data["possessions_source"] = source
    await cache_put(ctx, match.organization_id, "match", match.id, version, data)
    return data


async def cache_get(
    ctx: Ctx, scope: str, scope_id: uuid.UUID, version: str
) -> dict[str, Any] | None:
    row = (
        await ctx.db.execute(
            select(StatsCache.version, StatsCache.data).where(
                StatsCache.scope == scope, StatsCache.scope_id == scope_id
            )
        )
    ).first()
    return dict(row.data) if row is not None and row.version == version else None


async def cache_put(
    ctx: Ctx,
    org_id: uuid.UUID,
    scope: str,
    scope_id: uuid.UUID,
    version: str,
    data: dict[str, Any],
) -> None:
    """Atomic upsert: concurrent first views must not collide on the unique key."""
    stmt = pg_insert(StatsCache).values(
        id=uuid.uuid4(),
        organization_id=org_id,
        scope=scope,
        scope_id=scope_id,
        version=version,
        data=data,
    )
    await ctx.db.execute(
        stmt.on_conflict_do_update(
            constraint="uq_stats_cache_scope",
            set_={"version": stmt.excluded.version, "data": stmt.excluded.data},
        )
    )


async def set_kickoff(ctx: Ctx, match_id: uuid.UUID, period: int, t_ms: int) -> Match:
    """Store the video time of a half's throw-off and align events that only have a clock time."""
    match = await get_match(ctx, match_id, Action.EVENT_WRITE)
    match.kickoff_ms = {**(match.kickoff_ms or {}), str(period): t_ms}
    events = (
        await ctx.db.scalars(
            select(Event).where(
                Event.match_id == match.id, Event.period == period, Event.clock_s.is_not(None)
            )
        )
    ).all()
    for e in events:
        if e.source in ("official_feed", "paper_report") or e.t_ms is None:
            e.t_ms = video_from_clock(match, period, e.clock_s or 0.0)
    return match


# ---- official feed import (BRIEF 7.4): generic CSV/JSON, nothing is scraped ---------------

FEED_EVENTS: dict[str, dict[str, str]] = {
    "goal": {"type": "shot", "outcome": "goal"},
    "tor": {"type": "shot", "outcome": "goal"},
    "miss": {"type": "shot", "outcome": "miss"},
    "fehlwurf": {"type": "shot", "outcome": "miss"},
    "save": {"type": "shot", "outcome": "save"},
    "parade": {"type": "shot", "outcome": "save"},
    "post": {"type": "shot", "outcome": "post"},
    "pfosten": {"type": "shot", "outcome": "post"},
    "blocked": {"type": "shot", "outcome": "blocked"},
    "7m_goal": {"type": "shot", "outcome": "goal", "shot_type": "penalty"},
    "7m_miss": {"type": "shot", "outcome": "miss", "shot_type": "penalty"},
    "7m_save": {"type": "shot", "outcome": "save", "shot_type": "penalty"},
    "turnover": {"type": "turnover"},
    "technischer_fehler": {"type": "turnover"},
    "2min": {"type": "suspension_2min"},
    "yellow": {"type": "yellow_card"},
    "gelb": {"type": "yellow_card"},
    "red": {"type": "red_card"},
    "rot": {"type": "red_card"},
    "timeout": {"type": "timeout"},
    "7m": {"type": "seven_meter_awarded"},
}
OWN_ALIASES = {"own", "home_team", "us", "wir", "eigene", "h"}
OPP_ALIASES = {"opponent", "opp", "them", "gegner", "g"}


def _parse_clock(value: str) -> float:
    v = value.strip()
    m = re.fullmatch(r"(\d{1,3}):(\d{2})", v)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    return float(v)


async def import_feed(ctx: Ctx, match_id: uuid.UUID, data: bytes, filename: str) -> dict[str, Any]:
    """Columns: period, clock (mm:ss game clock), team (own/opponent), event, number."""
    match = await get_match(ctx, match_id, Action.EVENT_WRITE)
    text = data.decode("utf-8-sig", errors="replace")
    rows: list[dict[str, Any]]
    if filename.lower().endswith(".json"):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ProblemError(422, "invalid-feed", "Not valid JSON") from exc
        rows = parsed.get("events", parsed) if isinstance(parsed, dict) else parsed
    else:
        delimiter = ";" if text.count(";") > text.count(",") else ","
        rows = list(csv.DictReader(io.StringIO(text), delimiter=delimiter))
    numbers = {
        n: pid
        for n, pid in (
            await ctx.db.execute(
                select(RosterEntry.jersey_number, RosterEntry.player_id).where(
                    RosterEntry.season_id == match.season_id, RosterEntry.active.is_(True)
                )
            )
        ).all()
        if n is not None
    }
    created, skipped, errors = 0, 0, []
    for i, row in enumerate(rows[:2000], start=2):
        try:
            kind = FEED_EVENTS.get(str(row.get("event", "")).strip().lower())
            if kind is None:
                skipped += 1
                continue
            team = str(row.get("team", "")).strip().lower()
            side = "own" if team in OWN_ALIASES else "opponent" if team in OPP_ALIASES else None
            if side is None:
                raise ValueError(f"unknown team '{row.get('team')}'")
            period = int(row.get("period") or 1)
            clock = _parse_clock(str(row["clock"]))
            num_raw = str(row.get("number") or "").strip()
            number = int(num_raw) if num_raw.isdigit() else None
            player = numbers.get(number) if side == "own" and number is not None else None
            ev = Event(
                organization_id=match.organization_id,
                match_id=match.id,
                type=kind["type"],
                side=side,
                period=period,
                clock_s=clock,
                t_ms=video_from_clock(match, period, clock),
                number=number,
                player_id=player,
                outcome=kind.get("outcome"),
                shot_type=kind.get("shot_type"),
                shot_zone="penalty" if kind.get("shot_type") == "penalty" else None,
                source="official_feed",
                confidence=1.0,
                attributes={"feed_row": i},
            )
            ctx.db.add(ev)
            created += 1
        except (ValueError, KeyError, TypeError) as exc:
            errors.append(f"row {i}: {exc}")
    await ctx.db.flush()
    await audit.record(
        ctx,
        "events.imported",
        target_type="match",
        target_id=match.id,
        data={"created": created, "skipped": skipped, "errors": len(errors)},
    )
    return {"created": created, "skipped": skipped, "errors": errors[:50]}


async def shot_export(ctx: Ctx, match_id: uuid.UUID) -> dict[str, Any]:
    """P2 preparation (goalkeeper anticipation trainer): shots with metadata and the video times in
    the goal cameras. Only own staff; opponent shooters by number only (4.9)."""
    match = await get_match(ctx, match_id, Action.CLIP_WRITE)
    cams = (
        await ctx.db.scalars(
            select(VideoAsset).where(
                VideoAsset.match_id == match.id,
                VideoAsset.role.in_([VideoRole.GOAL_CAM_LEFT, VideoRole.GOAL_CAM_RIGHT]),
            )
        )
    ).all()
    shots = (
        await ctx.db.scalars(
            select(Event)
            .where(Event.match_id == match.id, Event.type == "shot")
            .order_by(Event.period, Event.clock_s.nulls_last(), Event.t_ms.nulls_last())
        )
    ).all()
    numbers = {
        pid: n
        for pid, n in (
            await ctx.db.execute(
                select(RosterEntry.player_id, RosterEntry.jersey_number).where(
                    RosterEntry.season_id == match.season_id
                )
            )
        ).all()
    }
    return {
        "format_version": 1,
        "match_id": str(match.id),
        "cameras": [{"video_id": str(c.id), "role": c.role} for c in cams],
        "shots": [
            {
                "event_id": str(e.id),
                "side": e.side,
                "shooter_number": e.number
                if e.number is not None
                else numbers.get(e.player_id)
                if e.player_id
                else None,
                "x": e.x,
                "y": e.y,
                "shot_zone": e.shot_zone,
                "goal_zone": e.goal_zone,
                "shot_type": e.shot_type,
                "outcome": e.outcome,
                "release_ms": e.t_ms,
                "camera_ms": {
                    str(c.id): e.t_ms + c.time_offset_ms if e.t_ms is not None else None
                    for c in cams
                },
            }
            for e in shots
        ],
    }


async def match_possessions(ctx: Ctx, match_id: uuid.UUID) -> dict[str, object]:
    """Possession phases of a match (from video tracking or imports) and a summary per side:
    number of attacks, average length and share of the observed time."""
    match = await get_match(ctx, match_id)
    rows = (
        await ctx.db.scalars(
            select(Possession).where(Possession.match_id == match.id).order_by(Possession.start_ms)
        )
    ).all()
    phases = [
        {
            "side": p.side,
            "start_ms": p.start_ms,
            "end_ms": p.end_ms,
            "outcome": p.outcome,
            "phase": p.phase,
            "confidence": round(p.confidence, 3),
            "source": p.source,
        }
        for p in rows
    ]
    total = sum(max(0, p.end_ms - p.start_ms) for p in rows) or 1
    summary: dict[str, dict[str, float]] = {}
    for side in ("own", "opponent"):
        mine = [p for p in rows if p.side == side]
        dur = sum(max(0, p.end_ms - p.start_ms) for p in mine)
        summary[side] = {
            "count": len(mine),
            "fast_breaks": sum(p.phase == "fast_break" for p in mine),
            "avg_s": round(dur / len(mine) / 1000, 1) if mine else 0.0,
            "share": round(dur / total, 3),
        }
    return {
        "phases": phases,
        "summary": summary,
        "estimated": any(p.source != "manual" for p in rows),
    }

"""Automatic events from the analysis (addendum 01, A3, principle P1).

The pipeline's event baseline (throw-offs, goals inferred from throw-offs, possession phases, side
changes) is stored with source "heuristic" and its confidence. A re-analysis replaces the previous
automatic rows. Events a person entered (tagging, import, correction) always win: an automatic
goal close to a manual one is dropped. The opening throw-offs set the match clock if nobody did.
An imported official report (services/official_report.py) has every goal: overlay goals close to
one of its goals are dropped and no goals are estimated from throw-offs.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import delete, select

from handball_api.models import Event, Match, Possession, RosterEntry
from handball_api.services.context import Ctx
from handball_api.services.events import clock_from_video, video_from_clock

SOURCE = "heuristic"
OVERLAY = "scoreboard_ocr"
OFFICIAL = "official_report"
MIN_CONFIDENCE = 0.5
DEDUPE_MS = 5000
OVERLAY_DEDUPE_MS = 20000  # the overlay is updated a few seconds after the goal


def _side(team: object) -> str | None:
    return {"home": "own", "away": "opponent"}.get(str(team))


def _overlay_clock(segments: list[dict[str, int]], t_ms: int) -> int | None:
    """Match clock (s) shown by the overlay at a video time: inside a run it counts, between runs
    it stands where the previous run ended."""
    before = [s for s in segments if s["start_ms"] <= t_ms]
    if not before:
        return None
    s = before[-1]
    return int(s["start_clock_s"] + (min(t_ms, s["end_ms"]) - s["start_ms"]) / 1000)


async def _align_official(ctx: Ctx, match: Match) -> None:
    """Official report events imported before the throw-off times were known get their video
    time now, so the overlay goals are matched against them."""
    rows = await ctx.db.scalars(
        select(Event).where(
            Event.match_id == match.id,
            Event.source == OFFICIAL,
            Event.t_ms.is_(None),
            Event.clock_s.is_not(None),
        )
    )
    for e in rows.all():
        e.t_ms = video_from_clock(match, e.period, e.clock_s or 0.0)


async def _manual_goals(ctx: Ctx, match: Match) -> list[tuple[str, int]]:
    rows = await ctx.db.scalars(
        select(Event).where(
            Event.match_id == match.id,
            Event.type == "shot",
            Event.outcome == "goal",
            Event.t_ms.is_not(None),
            Event.source.not_in((SOURCE, OVERLAY)),
        )
    )
    return [(e.side, int(e.t_ms)) for e in rows.all() if e.t_ms is not None]


ALIGN_BEFORE_MS = 15000  # an attack that ended up to 15 s before the overlay changed scored
ALIGN_MAX_WINDOW_MS = 120_000  # hall scoreboard out of view for at most two minutes


def align_goals(goals: list[Event], possessions: list[Possession]) -> int:
    """Move each overlay goal to the end of the scoring side's attack just before the overlay
    changed, and mark that attack as a goal: the goal clip then shows the finish, not the restart.
    """
    moved = 0
    for g in goals:
        if g.t_ms is None:
            continue
        # hall scoreboard: the goal lies anywhere since the board last showed the old score
        window = (g.attributes or {}).get("window_ms")
        before = (
            max(ALIGN_BEFORE_MS, min(ALIGN_MAX_WINDOW_MS, int(window)))
            if window
            else ALIGN_BEFORE_MS
        )
        cands = [
            p
            for p in possessions
            if p.side == g.side and g.t_ms - before <= p.end_ms <= g.t_ms + 2000
        ]
        if not cands:
            continue
        p = max(cands, key=lambda c: c.end_ms)
        if (g.attributes or {}).get("position_source"):  # the throw time is known: keep it
            p.outcome = "goal"
            moved += 1
            continue
        g.attributes = {**(g.attributes or {}), "overlay_ms": g.t_ms}
        if g.clock_s is not None:
            g.clock_s = round(g.clock_s - (g.t_ms - p.end_ms) / 1000, 1)
        g.t_ms = p.end_ms
        p.outcome = "goal"
        moved += 1
    return moved


async def apply_scoreboard(
    ctx: Ctx, match: Match, overlay: dict[str, Any] | None, created_out: list[Event] | None = None
) -> dict[str, int]:
    """Goals and match clock read from a broadcast overlay (BRIEF 7.2 stage 10). The left team of
    an overlay is the home team. The overlay clock sets the throw-off times nobody set yet, and the
    final score when the video reaches the end of the match and no result is stored."""
    await ctx.db.execute(delete(Event).where(Event.match_id == match.id, Event.source == OVERLAY))
    if not overlay:
        return {"overlay_goals": 0}
    left = "own" if match.is_home else "opponent"
    right = "opponent" if left == "own" else "own"
    segments = sorted(overlay.get("clock") or [], key=lambda s: int(s["start_ms"]))
    period_s = match.period_s

    k = dict(match.kickoff_ms or {})
    for seg in segments:
        clock, start = int(seg["start_clock_s"]), int(seg["start_ms"])
        half = "1" if clock < period_s else "2"
        if half not in k:
            # negative when the video starts after the throw-off (clips, late recording)
            k[half] = start - (clock - (period_s if half == "2" else 0)) * 1000
    if k != (match.kickoff_ms or {}):
        match.kickoff_ms = k
    await _align_official(ctx, match)

    manual = await _manual_goals(ctx, match)
    # the overlay names the scorer after a goal ("7 Lisa ZIMMERLI"): own players by shirt number
    roster: dict[int, Any] = {
        n: pid
        for n, pid in (
            await ctx.db.execute(
                select(RosterEntry.jersey_number, RosterEntry.player_id).where(
                    RosterEntry.season_id == match.season_id,
                    RosterEntry.team_id == match.team_id,
                    RosterEntry.active.is_(True),
                )
            )
        ).all()
        if n is not None
    }
    created = 0
    for g in overlay.get("goals") or []:
        side, t_ms = (left if g.get("side") == "left" else right), int(g["t_ms"])
        if any(s == side and abs(t - t_ms) <= OVERLAY_DEDUPE_MS for s, t in manual):
            continue
        shot = g.get("shot") if isinstance(g.get("shot"), dict) else None
        if shot and shot.get("t_ms") is not None:
            t_ms = int(shot["t_ms"])  # the scorer closest to goal: about the throw
        shown = _overlay_clock(segments, t_ms)
        if shown is not None:
            period, clock_s = (1 if shown < period_s else 2), float(shown)
        else:
            derived = clock_from_video(match, t_ms)
            period, clock_s = derived if derived else (1, None)  # type: ignore[assignment]
        score = list(g.get("score") or [])
        own_score = score if left == "own" else score[::-1]
        scorer = g.get("scorer") if isinstance(g.get("scorer"), dict) else None
        number = int(scorer["number"]) if scorer and scorer.get("number") is not None else None
        attrs: dict[str, Any] = {"score": own_score}
        if g.get("window_ms") is not None:
            attrs["window_ms"] = int(g["window_ms"])
        if scorer and scorer.get("name"):
            attrs["scorer_name"] = str(scorer["name"])[:80]
        if shot:
            attrs["position_source"] = str(shot.get("method", "nearest"))
        event = Event(
            organization_id=match.organization_id,
            match_id=match.id,
            type="shot",
            side=side,
            outcome="goal",
            t_ms=t_ms,
            period=period,
            clock_s=clock_s,
            source=OVERLAY,
            confidence=0.8 if overlay.get("source") == "hall_scoreboard" else 0.95,
            number=number,
            player_id=roster.get(number) if side == "own" and number is not None else None,
            x=float(shot["x"]) if shot else None,
            y=float(shot["y"]) if shot else None,
            attributes=attrs,
        )
        ctx.db.add(event)
        if created_out is not None:
            created_out.append(event)
        created += 1

    final = overlay.get("last_score")
    if segments and final and match.score_own is None and match.score_opponent is None:
        last = segments[-1]
        shown_end = last["start_clock_s"] + (last["end_ms"] - last["start_ms"]) / 1000
        if shown_end >= 2 * period_s - 90:  # the video reaches the final whistle
            match.score_own, match.score_opponent = (
                (final[0], final[1]) if left == "own" else (final[1], final[0])
            )
    await ctx.db.flush()
    return {"overlay_goals": created}


async def apply(
    ctx: Ctx,
    match: Match,
    payload: dict[str, Any] | None,
    overlay: dict[str, Any] | None = None,
) -> dict[str, int]:
    """Overlay first (exact goals and clock), then the position heuristics; a heuristic goal is
    dropped when the overlay gave goals."""
    overlay_goals: list[Event] = []
    sb = await apply_scoreboard(ctx, match, overlay, overlay_goals)
    if not payload:
        return {"events": 0, "possessions": 0, **sb}
    await ctx.db.execute(delete(Event).where(Event.match_id == match.id, Event.source == SOURCE))
    await ctx.db.execute(
        delete(Possession).where(Possession.match_id == match.id, Possession.source == SOURCE)
    )
    found = list(payload.get("events") or [])
    official_goals = await ctx.db.scalar(
        select(Event.id)
        .where(
            Event.match_id == match.id,
            Event.source == OFFICIAL,
            Event.type == "shot",
            Event.outcome == "goal",
        )
        .limit(1)
    )

    # match clock from the opening throw-offs (first one, first one after a side change)
    k = dict(match.kickoff_ms or {})
    side_changes = sorted(int(e["t_ms"]) for e in found if e.get("type") == "side_change")
    throw_offs = sorted(int(e["t_ms"]) for e in found if e.get("type") == "throw_off")
    if "1" not in k and throw_offs:
        k["1"] = throw_offs[0]
    if "2" not in k and side_changes:
        after = [t for t in throw_offs if t >= side_changes[0] - 2000]
        if after:
            k["2"] = after[0]
    if k != (match.kickoff_ms or {}):
        match.kickoff_ms = k

    manual_goals = [
        (e.side, e.t_ms)
        for e in (
            await ctx.db.scalars(
                select(Event).where(
                    Event.match_id == match.id,
                    Event.type == "shot",
                    Event.outcome == "goal",
                    Event.t_ms.is_not(None),
                )
            )
        ).all()
    ]
    created = 0
    for e in found:
        kind, side, t_ms = e.get("type"), _side(e.get("team")), int(e["t_ms"])
        conf = float(e.get("confidence", 0))
        if kind not in ("goal", "throw_off") or side is None or conf < MIN_CONFIDENCE:
            continue
        if kind == "goal" and (sb["overlay_goals"] or official_goals is not None):
            continue
        if kind == "goal" and any(
            s == side and t is not None and abs(t - t_ms) <= DEDUPE_MS for s, t in manual_goals
        ):
            continue
        derived = clock_from_video(match, t_ms)
        period, clock = derived if derived else (1, None)
        attrs = {k2: v for k2, v in e.items() if k2 not in ("t_ms", "type", "team", "confidence")}
        ctx.db.add(
            Event(
                organization_id=match.organization_id,
                match_id=match.id,
                type="shot" if kind == "goal" else "throw_off",
                side=side,
                outcome="goal" if kind == "goal" else None,
                t_ms=t_ms,
                period=period,
                clock_s=clock,
                source=SOURCE,
                confidence=conf,
                attributes=attrs,
            )
        )
        created += 1
    rows: list[Possession] = []
    for p in payload.get("possessions") or []:
        side = _side(p.get("team"))
        if side is None:
            continue
        rows.append(
            Possession(
                organization_id=match.organization_id,
                match_id=match.id,
                side=side,
                start_ms=int(p["start_ms"]),
                end_ms=int(p["end_ms"]),
                outcome=p.get("outcome"),
                phase=p.get("phase"),
                confidence=float(p.get("confidence", 0.5)),
                source=SOURCE,
            )
        )
    ctx.db.add_all(rows)
    aligned = align_goals(overlay_goals, rows)
    await ctx.db.flush()
    return {"events": created, "possessions": len(rows), "overlay_aligned": aligned, **sb}

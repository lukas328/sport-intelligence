"""Goal and shot candidates from the video analysis (handball_vision.goalcandidates): moments that
are probably goals (kind "goal") or shots of any outcome (kind "shot"), which the coach confirms
or rejects with one click. Both kinds live in one table and one review flow; the kind only says
which list (score, rate) proposed the moment.

- `store` (analysis result of the match's main video): the open candidates of the video are
  replaced; reviewed ones stay (a rejected candidate is a hard negative for training, a confirmed
  one is a shot with its outcome), and a new candidate this close to a reviewed one of its kind is
  the same moment and is not added again. Each candidate gets a suggested side: the side whose
  attack (automatic possession) ended just before it.
- `listing` (per kind): the candidates with the event they are already covered by (`known`):
  * goal candidates follow the dedupe rules of the automatic events (auto_events): an overlay or
    official goal within OVERLAY_DEDUPE_MS (the overlay changes a few seconds after the goal;
    official times come from the clock), any other goal (tagged, corrected, a confirmed
    candidate) or a shot confirmed on a candidate within NMS_MS (the candidates' own spacing);
    an event whose video time lies outside the video (a report goal before a clip starts) covers
    nothing;
  * shot candidates: any shot whose video time is known (tagged, courtside mark, a confirmed
    candidate, an overlay goal, a report entry confirmed on the video) within NMS_MS, overlay
    goals within OVERLAY_DEDUPE_MS.
  Shot candidates also get a `suggestion` from the official report: the report shot nearest to
  the candidate's estimated shot time (match_clock: overlay clock, confirmed entries and
  throw-offs as anchors), within SUGGEST_MS plus the uncertainty of that time (at most
  SUGGEST_MAX_MS), each entry suggested once. Confirming without a side takes the suggestion:
  one key. `official` lists the report's shots with where they are on the video. Computed when
  read, so a report imported later still merges them.
- `review`: confirm, reject, or undo. Confirming a candidate with a report entry (given, or the
  suggestion) pins that entry to the video: the entry keeps its player and outcome and takes the
  candidate's time (attributes.video, as an overlay goal gives an official goal its time); no
  second event is made. Otherwise a shot event of the chosen side and outcome (default goal for
  goal candidates), source "goal_candidate", at the estimated time; an automatic throw-off goal
  of that side close to it is superseded. Undo or reject removes the event or unpins the entry.
  Every review goes to the audit log.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select

from handball_api.core.clock import format_clock
from handball_api.core.errors import ProblemError
from handball_api.models import Event, GoalCandidate, Match, Possession, VideoAsset
from handball_api.schemas.events import EventIn
from handball_api.services import audit, match_clock, roster, timeline
from handball_api.services import events as event_service
from handball_api.services.auto_events import (
    CANDIDATE,
    OFFICIAL,
    OVERLAY,
    OVERLAY_DEDUPE_MS,
    SOURCE,
)
from handball_api.services.context import Ctx
from handball_api.services.events import clock_from_video, video_from_clock
from handball_api.services.matches import get_match, timeline_duration_ms
from handball_api.services.policies import Action

GOAL_SOURCE = CANDIDATE  # shot events confirmed from a candidate
NMS_MS = 8000  # candidates are at least this far apart
SAME_MOMENT_MS = 5000  # an answered goal and a new candidate this close are the same goal
SIDE_BEFORE_MS = 12_000  # an attack that ended this long before the goal scored it
KINDS = ("goal", "shot")
RATES = {"goal": (1, 2, 4), "shot": (2, 4, 6)}
DEFAULT_RATE = {"goal": 2, "shot": 4}
REVIEWED = ("confirmed", "rejected")
SIDES = ("own", "opponent")
OUTCOMES = ("goal", "save", "miss", "post", "blocked")
SUGGEST_MS = 8000  # report shot - estimated shot time, when the clock maps exactly
SUGGEST_MAX_MS = 20_000  # ... and at most (the clock map's uncertainty added)


def _int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _rows(found: dict[str, Any] | None) -> list[dict[str, Any]]:
    return [r for r in (found or {}).get("candidates") or [] if isinstance(r, dict)]


async def store(
    ctx: Ctx, match: Match, asset: VideoAsset, found: dict[str, Any] | None, pipeline: str | None
) -> dict[str, int]:
    """Candidates of a new analysis of the match's main video (`found` is the worker's
    `goal_candidates`, with the shot candidates under "shots"; None when the video was too short
    or nobody was seen)."""
    await ctx.db.execute(
        delete(GoalCandidate).where(
            GoalCandidate.video_asset_id == asset.id, GoalCandidate.status == "open"
        )
    )
    reviewed: dict[str, list[int]] = {k: [] for k in KINDS}
    for c in (
        await ctx.db.scalars(select(GoalCandidate).where(GoalCandidate.video_asset_id == asset.id))
    ).all():
        reviewed.setdefault(c.kind, []).append(c.goal_ms)
    shots = (found or {}).get("shots")
    lists = {"goal": found, "shot": shots if isinstance(shots, dict) else None}
    counts = {"goal_candidates": 0, "shot_candidates": 0}
    if not any(_rows(v) for v in lists.values()):
        return counts
    attacks = (
        await ctx.db.scalars(
            select(Possession).where(Possession.match_id == match.id, Possession.source == SOURCE)
        )
    ).all()
    for kind, part in lists.items():
        template = str((part or {}).get("template") or "")[:20] or None
        rates = RATES[kind]
        for r in _rows(part):
            t_ms = _int(r.get("t_ms"), -1)
            goal_ms = _int(r.get("goal_ms"), t_ms)
            # a moment already answered keeps its answer when the analysis runs again (a moved
            # court, real-video test F3): the same goal within 5 s is not asked a second time,
            # a goal 6 s or more apart is (F4)
            if t_ms < 0 or any(abs(goal_ms - t) < SAME_MOMENT_MS for t in reviewed[kind]):
                continue
            rate = _int(r.get("rate"), max(rates))
            ctx.db.add(
                GoalCandidate(
                    organization_id=match.organization_id,
                    match_id=match.id,
                    video_asset_id=asset.id,
                    kind=kind,
                    t_ms=t_ms,
                    goal_ms=goal_ms,
                    start_ms=_int(r.get("start_ms"), max(0, t_ms - 10_000)),
                    end_ms=_int(r.get("end_ms"), t_ms + 4000),
                    score=float(r.get("score") or 0.0),
                    rate=rate if rate in rates else max(rates),
                    rank=_int(r.get("rank")),
                    suggested_side=suggest_side(attacks, goal_ms),
                    status="open",
                    template_version=template,
                    pipeline_version=pipeline,
                )
            )
            counts[f"{kind}_candidates"] += 1
    await ctx.db.flush()
    return counts


def suggest_side(attacks: Any, goal_ms: int) -> str | None:
    """The side whose attack ended last before the goal (as overlay goals are aligned)."""
    near = [p for p in attacks if goal_ms - SIDE_BEFORE_MS <= p.end_ms <= goal_ms + 3000]
    return max(near, key=lambda p: p.end_ms).side if near else None


# ---- what is already known ----------------------------------------------------------------


def _pinned(e: Event) -> dict[str, Any] | None:
    """The video data of a report entry whose video time is known (overlay goal, confirmed
    candidate)."""
    v = (e.attributes or {}).get("video")
    return v if isinstance(v, dict) and v.get("t_ms") is not None else None


def _video_ms(e: Event) -> int | None:
    v = _pinned(e) if e.source == OFFICIAL else None
    return int(v["t_ms"]) if v is not None else e.t_ms


def _covers(c: GoalCandidate, e: Event, length_ms: int | None = None) -> int | None:
    """Distance (ms) at which event `e` covers candidate `c`, None when it does not. An event
    whose video time lies before the start or after the end of the candidate's video (`length_ms`)
    is not on it: a report goal at 12:26 does not cover a candidate early in a clip from 12:40,
    although the 20 s window of clock times would reach it."""
    if c.event_id is not None and e.id == c.event_id:
        return None
    t = _video_ms(e)
    if t is None or t < 0 or (length_ms is not None and t > length_ms):
        return None
    d = abs(int(t) - c.t_ms)
    if c.kind == "goal":
        if e.outcome == "goal":
            window = OVERLAY_DEDUPE_MS if e.source in (OVERLAY, OFFICIAL) else NMS_MS
        else:  # a save or miss confirmed on another candidate at this moment
            window = NMS_MS if e.source == CANDIDATE or _pinned(e) else -1
    elif e.source == OFFICIAL and _pinned(e) is None:
        window = -1  # time from the clock: a suggestion, not a known shot
    else:
        window = OVERLAY_DEDUPE_MS if e.source == OVERLAY else NMS_MS
    return d if d <= window else None


def _covered(
    c: GoalCandidate, shots: list[Event], lengths: dict[uuid.UUID, int | None] | None = None
) -> Event | None:
    """The shot a candidate is already covered by, nearest first (`lengths`: video length per
    asset, where known)."""
    best: tuple[int, Event] | None = None
    length = (lengths or {}).get(c.video_asset_id)
    for e in shots:
        d = _covers(c, e, length)
        if d is not None and (best is None or d < best[0]):
            best = (d, e)
    return best[1] if best else None


async def _shots(ctx: Ctx, match_id: uuid.UUID) -> list[Event]:
    return list(
        (
            await ctx.db.scalars(
                select(Event).where(
                    Event.match_id == match_id,
                    Event.type == "shot",
                    Event.source != SOURCE,  # estimated from throw-offs: what candidates check
                )
            )
        ).all()
    )


# ---- suggestions from the official report -------------------------------------------------


def _entry(
    e: Event, t_ms: int | None, unc: int | None, visible: set[uuid.UUID] | None = None
) -> dict[str, Any]:
    attrs = event_service.shown_attributes(e, visible)
    return {
        "event_id": e.id,
        "side": e.side,
        "outcome": e.outcome,
        "penalty": e.shot_type == "penalty",
        "number": e.number,
        "player_id": e.player_id,
        "name": attrs.get("name"),
        "period": e.period,
        "clock_s": e.clock_s,
        "official_time": attrs.get("official_time") or format_clock(e.clock_s),
        "t_ms": t_ms,
        "uncertainty_ms": unc,
    }


class _Report:
    """The report's shots on the video, and which candidate suggests which."""

    def __init__(self, match: Match, analysis: dict[str, Any] | None, shots: list[Event]) -> None:
        self.official = sorted(
            (e for e in shots if e.source == OFFICIAL),
            key=lambda e: (e.period, e.clock_s or 0.0),
        )
        self.map = match_clock.build(match, analysis, self.official)
        self.times = {e.id: match_clock.video_time(self.map, e) for e in self.official}
        self.by_candidate: dict[uuid.UUID, Event] = {}
        # players whose official names the reader may see (roster.visible_players)
        self.visible: set[uuid.UUID] | None = None

    def window(self, e: Event) -> int:
        unc = self.times[e.id][1]
        return min(SUGGEST_MS + (unc if unc is not None else SUGGEST_MAX_MS), SUGGEST_MAX_MS)

    def suggest(self, cands: list[GoalCandidate]) -> None:
        """Nearest pairs first, each candidate and each report shot once; confirmed candidates
        keep the entry they pinned."""
        taken = {c.event_id for c in cands if c.event_id is not None}
        free = [e for e in self.official if _pinned(e) is None and e.id not in taken]
        pairs = sorted(
            (abs(c.goal_ms - t), str(c.id), c, e)
            for c in cands
            for e in free
            if (t := self.times[e.id][0]) is not None and abs(c.goal_ms - t) <= self.window(e)
        )
        used: set[uuid.UUID] = set()
        for _, _, c, e in pairs:
            if c.id in self.by_candidate or e.id in used:
                continue
            self.by_candidate[c.id] = e
            used.add(e.id)

    def suggestion(self, c: GoalCandidate) -> dict[str, Any] | None:
        e = self.by_candidate.get(c.id)
        return None if e is None else _entry(e, *self.times[e.id], self.visible)

    def rows(self, cands: list[GoalCandidate], length_ms: int | None) -> dict[str, Any]:
        pinned = {c.event_id: c for c in cands if c.status == "confirmed" and c.event_id}
        suggested = {
            e.id: c for c_id, e in self.by_candidate.items() for c in cands if c.id == c_id
        }
        out = []
        for e in self.official:
            t, unc = self.times[e.id]
            row = _entry(e, t, unc, self.visible)
            cand = pinned.get(e.id) or suggested.get(e.id)
            if _pinned(e) is not None:
                status = "confirmed"
            elif e.id in suggested:
                status = "suggested"
            elif t is not None and (t < 0 or (length_ms is not None and t > length_ms)):
                status = "outside"
            else:
                status = "missing"
            row |= {"status": status, "candidate_id": cand.id if cand else None}
            out.append(row)
        counts = {s: sum(1 for r in out if r["status"] == s) for s in _OFFICIAL_STATUS}
        return {"counts": {"total": len(out), **counts}, "shots": out}


_OFFICIAL_STATUS = ("confirmed", "suggested", "missing", "outside")


# ---- listing ------------------------------------------------------------------------------


def _row(
    c: GoalCandidate, match: Match, known: Event | None, suggestion: dict[str, Any] | None
) -> dict[str, Any]:
    derived = clock_from_video(match, c.goal_ms)
    return {
        "id": c.id,
        "kind": c.kind,
        "video_asset_id": c.video_asset_id,
        "t_ms": c.t_ms,
        "goal_ms": c.goal_ms,
        "start_ms": c.start_ms,
        "end_ms": c.end_ms,
        "score": round(c.score, 3),
        "rate": c.rate,
        "suggested_side": c.suggested_side,
        "status": c.status,
        "side": c.side,
        "outcome": c.outcome,
        "event_id": c.event_id,
        "period": derived[0] if derived else None,
        "clock_s": derived[1] if derived else None,
        "known": None
        if known is None or c.status != "open"
        else {
            "event_id": known.id,
            "source": known.source,
            "side": known.side,
            "t_ms": _video_ms(known),
            "outcome": known.outcome,
        },
        "suggestion": suggestion if c.status == "open" and known is None else None,
    }


async def _assets(ctx: Ctx, cands: list[GoalCandidate]) -> dict[uuid.UUID, VideoAsset]:
    ids = {c.video_asset_id for c in cands}
    if not ids:
        return {}
    rows = (await ctx.db.scalars(select(VideoAsset).where(VideoAsset.id.in_(ids)))).all()
    return {a.id: a for a in rows}


async def _lengths(ctx: Ctx, cands: list[GoalCandidate]) -> dict[uuid.UUID, int | None]:
    """Length (ms) of the match timeline per asset of the candidates (their times are on it),
    None where unknown."""
    if not cands:
        return {}
    length = await timeline_duration_ms(ctx, cands[0].match_id)
    return dict.fromkeys(await _assets(ctx, cands), length)


async def _candidates(ctx: Ctx, match: Match, kind: str) -> list[GoalCandidate]:
    return list(
        (
            await ctx.db.scalars(
                select(GoalCandidate)
                .where(GoalCandidate.match_id == match.id, GoalCandidate.kind == kind)
                .order_by(GoalCandidate.t_ms)
            )
        ).all()
    )


async def _report(
    ctx: Ctx, match: Match, cands: list[GoalCandidate], shots: list[Event]
) -> tuple[_Report, int | None]:
    """The report's shots and their suggestions for the open, uncovered candidates (`cands`:
    all of a kind; the newest analysed video's overlay clock maps the report)."""
    # the candidates' times are on the match timeline: its length over all parts (Q-VIDEO-PARTS)
    assets = await _assets(ctx, cands)
    rep = _Report(match, await timeline.clock_analysis(ctx, match.id), shots)
    rep.visible = await roster.visible_players(ctx, match.team_id, match.season_id)
    length = await timeline_duration_ms(ctx, match.id) if assets else None
    lengths: dict[uuid.UUID, int | None] = dict.fromkeys(assets, length)
    rep.suggest([c for c in cands if c.status == "open" and _covered(c, shots, lengths) is None])
    return rep, length


async def listing(ctx: Ctx, match_id: uuid.UUID, kind: str = "goal") -> dict[str, Any]:
    if kind not in KINDS:
        raise ProblemError(422, "invalid-kind", "kind is goal or shot")
    match = await get_match(ctx, match_id)
    cands = await _candidates(ctx, match, kind)
    shots = await _shots(ctx, match.id)
    rep: _Report | None = None
    length: int | None = None
    if kind == "shot":
        rep, length = await _report(ctx, match, cands, shots)
    lengths = await _lengths(ctx, cands)
    rows = [
        _row(c, match, _covered(c, shots, lengths), rep.suggestion(c) if rep else None)
        for c in cands
    ]
    open_rows = [r for r in rows if r["status"] == "open" and r["known"] is None]
    versions = sorted({c.template_version for c in cands if c.template_version})
    rates = RATES[kind]
    return {
        "kind": kind,
        "template": versions[-1] if versions else None,
        "rates": list(rates),
        "default_rate": DEFAULT_RATE[kind],
        "counts": {
            "total": len(rows),
            "open": len(open_rows),
            "open_by_rate": {str(r): sum(1 for x in open_rows if x["rate"] <= r) for r in rates},
            "confirmed": sum(1 for r in rows if r["status"] == "confirmed"),
            "rejected": sum(1 for r in rows if r["status"] == "rejected"),
            "known": sum(1 for r in rows if r["known"] is not None),
            "suggested": sum(1 for r in open_rows if r["suggestion"] is not None),
        },
        "candidates": rows,
        "official": rep.rows(cands, length) if rep is not None and rep.official else None,
    }


# ---- review -------------------------------------------------------------------------------


def _unpin(match: Match, e: Event) -> None:
    """A report entry back to its time from the clock."""
    attrs = dict(e.attributes or {})
    v = attrs.pop("video", None)
    before = v.get("clock_t_ms") if isinstance(v, dict) else None
    e.attributes = attrs
    if before is not None:
        e.t_ms = int(before)
    elif e.clock_s is not None:
        e.t_ms = video_from_clock(match, e.period, float(e.clock_s))


async def _release(ctx: Ctx, match: Match, c: GoalCandidate) -> uuid.UUID | None:
    """The event a confirmation made removed (still this candidate's), or the report entry it
    pinned unpinned."""
    if c.event_id is None:
        return None
    ev = await ctx.db.get(Event, c.event_id)
    gone = None
    if ev is not None:
        v = _pinned(ev)
        if ev.source == OFFICIAL and v is not None and v.get("candidate_id") == str(c.id):
            _unpin(match, ev)
        elif (ev.attributes or {}).get("goal_candidate") == str(c.id):
            await event_service.delete_event(ctx, ev.id)
            gone = ev.id
    c.event_id = None
    return gone


def _pin(e: Event, c: GoalCandidate) -> None:
    e.attributes = {
        **(e.attributes or {}),
        "video": {
            "source": CANDIDATE,
            "t_ms": c.goal_ms,
            "clock_s": e.clock_s,
            "confidence": 1.0,
            "candidate_id": str(c.id),
            "clock_t_ms": e.t_ms,
        },
    }
    e.t_ms = c.goal_ms


async def _official_entry(
    ctx: Ctx, match: Match, c: GoalCandidate, event_id: uuid.UUID | None, shots: list[Event]
) -> Event | None:
    """The report entry a confirmation pins: the one given, else the candidate's suggestion."""
    if event_id is not None:
        e = await ctx.db.get(Event, event_id)
        if e is None or e.match_id != match.id or e.source != OFFICIAL or e.type != "shot":
            raise ProblemError(422, "invalid-official-event", "Not a shot of the official report")
        return e
    if c.kind != "shot":
        return None
    rep, _ = await _report(ctx, match, await _candidates(ctx, match, c.kind), shots)
    return rep.by_candidate.get(c.id)


async def review(
    ctx: Ctx,
    match_id: uuid.UUID,
    candidate_id: uuid.UUID,
    status: str | None,
    side: str | None,
    outcome: str | None = None,
    official_event_id: uuid.UUID | None = None,
    number: int | None = None,
    player_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Confirm (whose shot and its outcome; a report entry is pinned instead of a new event),
    reject or reopen (`status` None) a candidate."""
    match = await get_match(ctx, match_id, Action.EVENT_WRITE)
    c = await ctx.db.get(GoalCandidate, candidate_id)
    if c is None or c.match_id != match.id:
        raise ProblemError(404, "not-found", "Candidate not found")
    before = (c.status, c.side, c.outcome)
    shots = await _shots(ctx, match.id)
    superseded: list[str] = []
    removed = None
    official: Event | None = None
    if status == "confirmed":
        if c.status == "confirmed" and c.event_id is not None and official_event_id is None:
            current = await ctx.db.get(Event, c.event_id)
            if current is not None and current.source == OFFICIAL:
                official = current  # pinned before: a repeated confirmation keeps it
        if official is None and (official_event_id is not None or side is None):
            official = await _official_entry(ctx, match, c, official_event_id, shots)
        if official is not None:
            if (side or official.side) != official.side or (
                outcome or official.outcome
            ) != official.outcome:
                raise ProblemError(
                    422, "official-differs", "Side or outcome differ from the report entry"
                )
            side, outcome = official.side, official.outcome
        if side not in SIDES:
            raise ProblemError(422, "invalid-side", "A confirmed shot needs the side that shot")
        outcome = outcome or ("goal" if c.kind == "goal" else None)
        if outcome not in OUTCOMES:
            raise ProblemError(422, "invalid-outcome", "A confirmed shot needs its outcome")
        if c.status == "open":
            known = _covered(c, shots, await _lengths(ctx, [c]))
            if known is not None and (c.kind == "shot" or known.outcome == "goal"):
                raise ProblemError(409, "already-a-goal", "This moment is already a known shot")
        ev = await ctx.db.get(Event, c.event_id) if c.event_id else None
        mine = ev is not None and (ev.attributes or {}).get("goal_candidate") == str(c.id)
        if official is not None:
            if ev is None or ev.id != official.id:
                removed = await _release(ctx, match, c)
                if _pinned(official) is not None:
                    raise ProblemError(
                        409, "already-on-video", "This report entry already has its video time"
                    )
                _pin(official, c)
                c.event_id = official.id
        elif mine and ev is not None:
            # the new-event path checks the player in create_event; here the event is edited
            await event_service._check_players(ctx, match, player_id)
            ev.side, ev.outcome = str(side), outcome
            if number is not None:
                ev.number = number
            if player_id is not None:
                ev.player_id = player_id
        else:
            removed = await _release(ctx, match, c)
            created = await event_service.create_event(
                ctx,
                match.id,
                EventIn(
                    type="shot",
                    side=side,
                    outcome=outcome,
                    t_ms=c.goal_ms,
                    number=number,
                    player_id=player_id,
                    attributes={
                        "goal_candidate": str(c.id),
                        "candidate_kind": c.kind,
                        "clip": [c.start_ms, c.end_ms],
                    },
                ),
                source=GOAL_SOURCE,
            )
            c.event_id = created.id
        if outcome == "goal":
            # an automatic goal estimated from the throw-off is the same goal, now confirmed
            for g in await ctx.db.scalars(
                select(Event).where(
                    Event.match_id == match.id,
                    Event.source == SOURCE,
                    Event.type == "shot",
                    Event.outcome == "goal",
                    Event.side == side,
                    Event.t_ms.between(
                        c.goal_ms - OVERLAY_DEDUPE_MS, c.goal_ms + OVERLAY_DEDUPE_MS
                    ),
                )
            ):
                superseded.append(str(g.id))
                await ctx.db.delete(g)
        c.status, c.side, c.outcome = "confirmed", side, outcome
    else:
        removed = await _release(ctx, match, c)
        c.status, c.side, c.outcome = (
            ("rejected" if status == "rejected" else "open"),
            None,
            None,
        )
    c.reviewed_by_id = ctx.user_id if status is not None else None
    c.reviewed_at = datetime.now(UTC) if status is not None else None
    await ctx.db.flush()
    await audit.record(
        ctx,
        "match.goal_candidate_reviewed",
        target_type="match",
        target_id=match.id,
        data={
            "candidate_id": str(c.id),
            "kind": c.kind,
            "video_asset_id": str(c.video_asset_id),
            "t_ms": c.t_ms,
            "template": c.template_version,
            "review": status,
            "side": c.side,
            "outcome": c.outcome,
            "before": {"status": before[0], "side": before[1], "outcome": before[2]},
            "event_id": str(c.event_id) if c.event_id else None,
            "official_event_id": str(official.id) if official is not None else None,
            "removed_event_id": str(removed) if removed else None,
            "superseded": superseded,
        },
    )
    shots = await _shots(ctx, match.id)
    sugg = None
    if c.kind == "shot" and c.status == "open":
        rep, _ = await _report(ctx, match, await _candidates(ctx, match, c.kind), shots)
        sugg = rep.suggestion(c)
    return _row(c, match, _covered(c, shots, await _lengths(ctx, [c])), sugg)

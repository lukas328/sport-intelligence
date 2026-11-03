"""Typed queries over events of several matches (M10: assistant 5.1, statistics matrix 5.4).

Pure functions on already authorised data: the API loads a team's matches and events, these
functions filter, aggregate, group and compare. Every result carries its sample (numerator,
denominator, number of matches) so a text or a table can say how much data stands behind a number.
Definitions follow packages/metrics/DEFINITIONS.md.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any, Literal

from handball_metrics.model import Event, EventType
from handball_metrics.stats import zone_of
from handball_metrics.xg import expected_goal


@dataclass(frozen=True)
class MatchInfo:
    id: str
    date: str  # ISO date of the kickoff
    opponent: str | None
    score_own: int | None = None
    score_opponent: int | None = None
    kind: str = "match"  # match or training
    # opponent defence formation segments from the video analysis: (start_ms, end_ms, formation)
    opponent_formations: tuple[tuple[int, int, str], ...] = ()


@dataclass(frozen=True)
class Row:
    event: Event
    match: MatchInfo


@dataclass(frozen=True)
class Filter:
    match_ids: tuple[str, ...] = ()
    last_n_matches: int | None = None
    opponent: str | None = None  # case-insensitive substring of the opponent name
    type: str | None = None
    side: Literal["own", "opponent"] | None = None
    outcome: str | None = None
    zone: str | None = None
    shot_type: str | None = None
    goal_zone: str | None = None
    number: int | None = None
    period: int | None = None
    minute_from: int | None = None  # match minute, 1-based, inclusive
    minute_to: int | None = None
    after_timeout_s: int | None = None  # only events up to N s after a timeout of the own team
    opponent_formation: str | None = None  # opponent defence at the moment (needs video analysis)
    play_id: str | None = None  # events linked to a play of the library (attributes.play_id)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> Filter:
        data = {k: v for k, v in (data or {}).items() if v is not None and v != ""}
        allowed = set(cls.__dataclass_fields__)
        unknown = set(data) - allowed
        if unknown:
            raise ValueError(f"unknown filter fields: {', '.join(sorted(unknown))}")
        if "match_ids" in data:
            data["match_ids"] = tuple(str(m) for m in data["match_ids"])
        return cls(**data)


def minute(e: Event) -> int | None:
    return int(e.clock_s // 60) + 1 if e.clock_s is not None else None


def ordered_matches(matches: Iterable[MatchInfo]) -> list[MatchInfo]:
    """Newest first."""
    return sorted(matches, key=lambda m: (m.date, m.id), reverse=True)


def _formation_at(m: MatchInfo, t_ms: int | None) -> str | None:
    if t_ms is None:
        return None
    for start, end, formation in m.opponent_formations:
        if start <= t_ms <= end:
            return formation
    return None


def _timeouts(rows: list[Row]) -> dict[str, list[tuple[int, float]]]:
    out: dict[str, list[tuple[int, float]]] = {}
    for r in rows:
        e = r.event
        if e.type is EventType.TIMEOUT and e.side.value == "own" and e.clock_s is not None:
            out.setdefault(r.match.id, []).append((e.period, e.clock_s))
    return out


def _after_timeout(e: Event, timeouts: list[tuple[int, float]], f: Filter) -> bool:
    if e.clock_s is None or not f.after_timeout_s:
        return False
    return any(p == e.period and 0 < e.clock_s - c <= f.after_timeout_s for p, c in timeouts)


def select(rows: list[Row], f: Filter) -> list[Row]:
    matches = {r.match.id: r.match for r in rows}
    allowed = set(matches)
    if f.match_ids:
        allowed &= set(f.match_ids)
    if f.opponent:
        needle = f.opponent.lower()
        allowed = {m for m in allowed if needle in (matches[m].opponent or "").lower()}
    if f.last_n_matches:
        newest = ordered_matches(matches[m] for m in allowed)[: max(0, f.last_n_matches)]
        allowed = {m.id for m in newest}
    timeouts = _timeouts(rows) if f.after_timeout_s else {}
    out: list[Row] = []
    for r in rows:
        e = r.event
        if r.match.id not in allowed:
            continue
        if f.type and e.type.value != f.type:
            continue
        if f.side and e.side.value != f.side:
            continue
        if f.outcome and e.outcome != f.outcome:
            continue
        if f.zone and zone_of(e) != f.zone:
            continue
        if f.shot_type and e.shot_type != f.shot_type:
            continue
        if f.goal_zone and e.goal_zone != f.goal_zone:
            continue
        if f.number is not None and e.number != f.number:
            continue
        if f.period and e.period != f.period:
            continue
        mi = minute(e)
        if f.minute_from and (mi is None or mi < f.minute_from):
            continue
        if f.minute_to and (mi is None or mi > f.minute_to):
            continue
        if f.after_timeout_s and not _after_timeout(e, timeouts.get(r.match.id, []), f):
            continue
        if f.opponent_formation and _formation_at(r.match, e.t_ms) != f.opponent_formation:
            continue
        if f.play_id and str(e.attributes.get("play_id") or "") != f.play_id:
            continue
        out.append(r)
    return out


# ---- metrics ------------------------------------------------------------------------------------

Pred = Callable[[Event], bool]


def _shot(e: Event) -> bool:
    return e.is_shot


def _goal(e: Event) -> bool:
    return e.is_goal


def _save(e: Event) -> bool:
    return e.is_shot and e.outcome == "save"


def _on_target(e: Event) -> bool:
    return e.is_shot and e.outcome in ("goal", "save")


def _penalty(e: Event) -> bool:
    return e.is_shot and e.shot_type == "penalty"


def _penalty_goal(e: Event) -> bool:
    return _penalty(e) and e.outcome == "goal"


def _fast_break_goal(e: Event) -> bool:
    return e.is_goal and (e.shot_type == "fast_break" or zone_of(e) == "fast_break")


def _turnover(e: Event) -> bool:
    return e.type is EventType.TURNOVER


def _suspension(e: Event) -> bool:
    return e.type is EventType.SUSPENSION


def _steal(e: Event) -> bool:
    return e.type is EventType.STEAL


@dataclass(frozen=True)
class MetricDef:
    kind: Literal["count", "ratio", "sum"]
    num: Pred
    den: Pred | None = None
    label: str = ""


METRICS: dict[str, MetricDef] = {
    "shots": MetricDef("count", _shot, label="shots"),
    "goals": MetricDef("count", _goal, label="goals (shots with outcome goal)"),
    "shooting_pct": MetricDef("ratio", _goal, _shot, "goals / shots"),
    "on_target_pct": MetricDef("ratio", _on_target, _shot, "(goals + saves) / shots"),
    "saves": MetricDef("count", _save, label="shots saved by the goalkeeper"),
    "save_pct": MetricDef("ratio", _save, _on_target, "saves / (goals + saves) of these shots"),
    "xg": MetricDef("sum", _shot, label="expected goals of these shots (estimate)"),
    "turnovers": MetricDef("count", _turnover, label="turnovers"),
    "steals": MetricDef("count", _steal, label="steals"),
    "suspensions": MetricDef("count", _suspension, label="2-minute suspensions"),
    "seven_m_goals": MetricDef("count", _penalty_goal, label="7 m goals"),
    "seven_m_pct": MetricDef("ratio", _penalty_goal, _penalty, "7 m goals / 7 m shots"),
    "fast_break_goals": MetricDef("count", _fast_break_goal, label="fast break goals"),
    "events": MetricDef("count", lambda e: True, label="events"),
}


def _attr(r: Row, key: str) -> str | None:
    v = r.event.attributes.get(key)
    return str(v) if v else None


GROUPS: dict[str, Callable[[Row], str | None]] = {
    "match": lambda r: r.match.id,
    "opponent": lambda r: r.match.opponent,
    "number": lambda r: str(r.event.number) if r.event.number is not None else None,
    "zone": lambda r: zone_of(r.event),
    "goal_zone": lambda r: r.event.goal_zone,
    "period": lambda r: str(r.event.period),
    "shot_type": lambda r: r.event.shot_type,
    "type": lambda r: r.event.type.value,
    "outcome": lambda r: r.event.outcome,
    "side": lambda r: r.event.side.value,
    "position": lambda r: _attr(r, "position"),
    "play": lambda r: _attr(r, "play_id"),
    "minute_10": lambda r: (
        f"{(m - 1) // 10 * 10 + 1}-{(m - 1) // 10 * 10 + 10}"
        if (m := minute(r.event)) is not None
        else None
    ),
}


@dataclass
class Value:
    value: float | None
    numerator: float
    denominator: int | None
    events: int  # events counted
    matches: int
    event_ids: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "numerator": self.numerator,
            "denominator": self.denominator,
            "events": self.events,
            "matches": self.matches,
        }


def compute(metric: str, rows: list[Row]) -> Value:
    if metric not in METRICS:
        raise ValueError(f"unknown metric {metric}")
    d = METRICS[metric]
    hits = [r for r in rows if d.num(r.event)]
    matches = len({r.match.id for r in rows})
    ids = [r.event.id for r in hits]
    if d.kind == "count":
        return Value(float(len(hits)), float(len(hits)), None, len(hits), matches, ids)
    if d.kind == "sum":
        total = sum(expected_goal(r.event.x, r.event.y, r.event.shot_type) for r in hits)
        return Value(round(total, 1), round(total, 1), len(hits), len(hits), matches, ids)
    assert d.den is not None
    base = [r for r in rows if d.den(r.event)]
    value = round(len(hits) / len(base), 3) if base else None
    # a ratio's evidence is its base (all shots of a shooting percentage, not only the goals)
    return Value(value, float(len(hits)), len(base), len(base), matches, [r.event.id for r in base])


def aggregate(rows: list[Row], metric: str, group_by: str | None = None) -> dict[str, Any]:
    total = compute(metric, rows)
    out: dict[str, Any] = {"metric": metric, "definition": METRICS[metric].label, **total.as_dict()}
    if group_by:
        if group_by not in GROUPS:
            raise ValueError(f"unknown grouping {group_by}")
        key = GROUPS[group_by]
        buckets: dict[str, list[Row]] = {}
        for r in rows:
            k = key(r)
            if k is not None:
                buckets.setdefault(k, []).append(r)
        groups = []
        for k, rs in buckets.items():
            v = compute(metric, rs)
            groups.append({"key": k, **v.as_dict()})
        groups.sort(key=lambda g: (g["value"] is None, -(g["value"] or 0), g["key"]))
        out["groups"] = groups
        out["group_by"] = group_by
    return out


def compare(rows: list[Row], metric: str, a: Filter, b: Filter) -> dict[str, Any]:
    va, vb = compute(metric, select(rows, a)), compute(metric, select(rows, b))
    diff = round(va.value - vb.value, 3) if va.value is not None and vb.value is not None else None
    return {
        "metric": metric,
        "definition": METRICS[metric].label,
        "a": va.as_dict(),
        "b": vb.as_dict(),
        "difference": diff,
        "note": "observation from the data, not proof of cause",
    }

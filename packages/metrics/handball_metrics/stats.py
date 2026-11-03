"""Match statistics from events. Exact definitions: packages/metrics/DEFINITIONS.md."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

from handball_court.zones import shot_zone
from handball_metrics.model import Event, EventType, Side
from handball_metrics.xg import VERSION as XG_VERSION
from handball_metrics.xg import expected_goal

SUSPENSION_S = 120


def _ratio(a: float, b: float) -> float | None:
    return round(a / b, 4) if b else None


@dataclass
class _Clock:
    """Orders events by match clock (falls back to video time, then input order)."""

    @staticmethod
    def key(e: Event, i: int) -> tuple[float, int]:
        if e.clock_s is not None:
            return (e.clock_s, i)
        if e.t_ms is not None:
            return (e.t_ms / 1000, i)
        return (float(i), i)


def zone_of(e: Event) -> str | None:
    if e.shot_zone:
        return e.shot_zone
    if e.shot_type == "penalty":
        return "penalty"
    if e.x is not None and e.y is not None:
        return shot_zone(e.x, e.y, fast_break=e.shot_type == "fast_break")
    return None


def situations(events: list[Event]) -> dict[str, str]:
    """Numerical situation per event id from active 2-minute suspensions (BRIEF 4.6).

    'equal', 'powerplay' (team has more players), 'shorthanded'; red cards count as 2 minutes
    for the team strength (simplification). Events without clock are 'unknown'.
    """
    timed = [e for e in events if e.clock_s is not None]
    pens = [
        (e.clock_s or 0.0, e.side) for e in timed if e.type in (EventType.SUSPENSION, EventType.RED)
    ]
    out: dict[str, str] = {}
    for e in events:
        if e.clock_s is None:
            out[e.id] = "unknown"
            continue
        active = Counter(side for start, side in pens if start <= e.clock_s < start + SUSPENSION_S)
        own_down, opp_down = active[Side.OWN], active[Side.OPPONENT]
        mine, theirs = (own_down, opp_down) if e.side is Side.OWN else (opp_down, own_down)
        out[e.id] = "equal" if mine == theirs else "powerplay" if mine < theirs else "shorthanded"
    return out


def _team_block(
    events: list[Event], side: Side, sit: dict[str, str], possessions: int | None
) -> dict[str, Any]:
    mine = [e for e in events if e.side is side]
    theirs = [e for e in events if e.side is side.other]
    shots = [e for e in mine if e.is_shot]
    on_target_shots = [e for e in shots if e.outcome != "blocked"]
    goals = [e for e in shots if e.outcome == "goal"]
    opp_shots = [e for e in theirs if e.is_shot]
    saves = [e for e in opp_shots if e.outcome == "save"]
    goals_against = [e for e in opp_shots if e.outcome == "goal"]
    turnovers = [e for e in mine if e.type is EventType.TURNOVER]
    zones: dict[str, dict[str, int]] = defaultdict(lambda: {"shots": 0, "goals": 0})
    goal_zones: dict[str, dict[str, int]] = defaultdict(lambda: {"shots": 0, "goals": 0})
    for e in shots:
        z = zone_of(e)
        if z:
            zones[z]["shots"] += 1
            zones[z]["goals"] += e.outcome == "goal"
        if e.goal_zone and e.outcome in ("goal", "save"):
            goal_zones[e.goal_zone]["shots"] += 1
            goal_zones[e.goal_zone]["goals"] += e.outcome == "goal"
    by_sit: dict[str, dict[str, int]] = defaultdict(lambda: {"shots": 0, "goals": 0})
    for e in shots:
        by_sit[sit.get(e.id, "unknown")]["shots"] += 1
        by_sit[sit.get(e.id, "unknown")]["goals"] += e.outcome == "goal"
    penalties = [e for e in shots if e.shot_type == "penalty" or zone_of(e) == "penalty"]
    xg = sum(expected_goal(e.x, e.y, e.shot_type) for e in shots if e.outcome != "blocked")
    return {
        "goals": len(goals),
        "shots": len(on_target_shots),  # excluding blocked shots (BRIEF 4.8)
        "shots_blocked": len(shots) - len(on_target_shots),
        "misses": sum(e.outcome == "miss" for e in shots),
        "posts": sum(e.outcome == "post" for e in shots),
        "shooting_pct": _ratio(len(goals), len(on_target_shots)),
        "saves": len(saves),
        "save_pct": _ratio(len(saves), len(saves) + len(goals_against)),
        "goals_against": len(goals_against),
        "turnovers": len(turnovers),
        "turnovers_by_type": dict(Counter(e.turnover_type or "other" for e in turnovers)),
        "steals": sum(e.type is EventType.STEAL for e in mine),
        "seven_m_awarded": sum(e.type is EventType.SEVEN_METER_AWARDED for e in mine),
        "seven_m_goals": sum(e.outcome == "goal" for e in penalties),
        "seven_m_shots": len(penalties),
        "fast_break_goals": sum(e.outcome == "goal" and zone_of(e) == "fast_break" for e in shots),
        "suspensions": sum(e.type is EventType.SUSPENSION for e in mine),
        "yellow_cards": sum(e.type is EventType.YELLOW for e in mine),
        "red_cards": sum(e.type is EventType.RED for e in mine),
        "timeouts": sum(e.type is EventType.TIMEOUT for e in mine),
        "possessions": possessions,
        "attack_efficiency": _ratio(len(goals), possessions or 0),
        "turnover_rate": _ratio(len(turnovers), possessions or 0),
        "zones": dict(zones),
        "goal_zones": dict(goal_zones),
        "by_situation": {
            k: {**v, "pct": _ratio(v["goals"], v["shots"])} for k, v in by_sit.items()
        },
        "xg": round(xg, 2),
    }


def _players(events: list[Event]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}

    def row(key: str, e: Event) -> dict[str, Any]:
        if key not in out:
            out[key] = {
                "side": e.side.value,
                "player_id": e.player_id,
                "number": e.number,
                "goals": 0,
                "shots": 0,
                "misses": 0,
                "posts": 0,
                "saved": 0,
                "blocked": 0,
                "turnovers": 0,
                "turnovers_by_type": Counter(),
                "suspensions": 0,
                "assists": 0,
                "seven_m_goals": 0,
                "seven_m_shots": 0,
                "xg": 0.0,
                "saves": 0,
            }
        return out[key]

    def key_of(e: Event, player_id: str | None = None) -> str | None:
        pid = player_id or e.player_id
        if pid:
            return f"p:{pid}"
        if e.number is not None:
            return f"{e.side.value}#{e.number}"
        return None

    for e in events:
        k = key_of(e)
        if e.is_shot and k:
            r = row(k, e)
            if e.outcome != "blocked":
                r["shots"] += 1
                r["xg"] = round(r["xg"] + expected_goal(e.x, e.y, e.shot_type), 3)
            r["goals"] += e.outcome == "goal"
            r["misses"] += e.outcome == "miss"
            r["posts"] += e.outcome == "post"
            r["saved"] += e.outcome == "save"
            r["blocked"] += e.outcome == "blocked"
            if e.shot_type == "penalty" or e.shot_zone == "penalty":
                r["seven_m_shots"] += 1
                r["seven_m_goals"] += e.outcome == "goal"
            if e.outcome == "goal" and e.assist_player_id:
                ak = key_of(e, e.assist_player_id)
                assert ak is not None
                row(ak, e)["assists"] += 1
        elif e.type is EventType.TURNOVER and k:
            r = row(k, e)
            r["turnovers"] += 1
            r["turnovers_by_type"][e.turnover_type or "other"] += 1
        elif e.type is EventType.SUSPENSION and k:
            row(k, e)["suspensions"] += 1
    # goalkeeper saves are credited to the goalkeeper recorded in attributes
    for e in events:
        gk = e.attributes.get("goalkeeper_id") if e.is_shot and e.outcome == "save" else None
        if gk:
            key = f"p:{gk}"
            if key not in out:
                out[key] = {
                    "side": e.side.other.value,
                    "player_id": gk,
                    "number": None,
                    "goals": 0,
                    "shots": 0,
                    "misses": 0,
                    "posts": 0,
                    "saved": 0,
                    "blocked": 0,
                    "turnovers": 0,
                    "turnovers_by_type": Counter(),
                    "suspensions": 0,
                    "assists": 0,
                    "seven_m_goals": 0,
                    "seven_m_shots": 0,
                    "xg": 0.0,
                    "saves": 0,
                }
            out[key]["saves"] += 1
    for r in out.values():
        r["turnovers_by_type"] = dict(r["turnovers_by_type"])
        r["shooting_pct"] = _ratio(r["goals"], r["shots"])
    return out


def _timeline(events: list[Event]) -> dict[str, Any]:
    ordered = [
        e
        for _, e in sorted(
            ((_Clock.key(e, i), e) for i, e in enumerate(events)), key=lambda t: t[0]
        )
    ]
    own = opp = 0
    points: list[dict[str, Any]] = [{"clock_s": 0.0, "own": 0, "opp": 0}]
    run_side: Side | None = None
    run_len = 0
    best: dict[Side, tuple[int, float | None]] = {Side.OWN: (0, None), Side.OPPONENT: (0, None)}
    run_start: float | None = None
    last_own: float = 0.0
    longest_drought = (0.0, 0.0, 0.0)  # seconds, from, to
    for e in ordered:
        if not e.is_goal:
            continue
        t = e.clock_s if e.clock_s is not None else (e.t_ms or 0) / 1000
        if e.side is Side.OWN:
            own += 1
            if t - last_own > longest_drought[0]:
                longest_drought = (t - last_own, last_own, t)
            last_own = t
        else:
            opp += 1
        points.append({"clock_s": t, "own": own, "opp": opp, "event_id": e.id})
        if e.side is run_side:
            run_len += 1
        else:
            run_side, run_len, run_start = e.side, 1, t
        if run_len > best[e.side][0]:
            best[e.side] = (run_len, run_start)
    return {
        "score": points,
        "final": {"own": own, "opp": opp},
        "best_run": {s.value: {"goals": n, "from_s": start} for s, (n, start) in best.items()},
        "longest_own_drought_s": {
            "seconds": round(longest_drought[0], 1),
            "from_s": longest_drought[1],
            "to_s": longest_drought[2],
        },
    }


def compute_match_stats(
    events: list[Event], possessions: dict[str, int] | None = None
) -> dict[str, Any]:
    sit = situations(events)
    poss = possessions or {}
    low_conf = [e for e in events if e.confidence < 0.6]
    return {
        "own": _team_block(events, Side.OWN, sit, poss.get("own")),
        "opponent": _team_block(events, Side.OPPONENT, sit, poss.get("opponent")),
        "players": _players(events),
        "timeline": _timeline(events),
        "quality": {
            "events": len(events),
            "low_confidence": len(low_conf),
            "sources": dict(Counter(e.source for e in events)),
        },
        "versions": {"metrics": "0.1.0", "xg": XG_VERSION},
    }

"""Insight engine (BRIEF 4.9, M7): a catalogue of rules over match stats and the season baseline.

Principles (keeps insights honest):
- every insight carries its numbers, its sample size and the events behind it (`evidence` filter),
- rates are compared with Wilson score intervals (90 %); an insight against the baseline only fires
  when the baseline lies outside the interval of the current value,
- minimum samples per rule (`MIN_*`), otherwise nothing is said,
- ranking by effect size times confidence; at most `limit` insights, strengths and weaknesses mixed,
- text is a template key plus parameters (rendered in the UI language); an optional LLM summary may
  only use numbers that appear in the insights (see the API's text generator and validator).
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any

Z90 = 1.645
MIN_SHOTS = 10
MIN_ZONE_SHOTS = 4
MIN_SEVEN_M = 3
MIN_KEEPER_FACED = 8
MIN_PLAYER_SHOTS = 5
MIN_BASELINE_MATCHES = 2
VERSION = "insights-1"


@dataclass
class Insight:
    id: str
    kind: str  # strength | weakness | info
    key: str  # i18n key, e.g. "insights.shooting_below"
    params: dict[str, Any]
    score: float  # ranking, 0..1
    sample: int
    evidence: dict[str, Any] = field(default_factory=dict)  # event list filter
    numbers: list[float] = field(default_factory=list)  # every number a text may cite

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["score"] = round(self.score, 3)
        return d


def wilson(k: int, n: int, z: float = Z90) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def _pct(v: float | None) -> int:
    return round((v or 0.0) * 100)


def _baseline_rate(
    baseline: list[dict[str, Any]], side: str, num: str, den: str
) -> tuple[int, int]:
    k = sum(int(b[side].get(num) or 0) for b in baseline)
    n = sum(int(b[side].get(den) or 0) for b in baseline)
    return k, n


def _vs_baseline(
    out: list[Insight],
    *,
    ident: str,
    k: int,
    n: int,
    bk: int,
    bn: int,
    higher_is_better: bool,
    key_good: str,
    key_bad: str,
    min_n: int,
    evidence: dict[str, Any],
) -> None:
    if n < min_n or bn < min_n:
        return
    rate, base = k / n, bk / bn
    lo, hi = wilson(k, n)
    if lo <= base <= hi:
        return
    better = (rate > base) == higher_is_better
    effect = abs(rate - base)
    distance = (lo - base) if rate > base else (base - hi)
    out.append(
        Insight(
            id=ident,
            kind="strength" if better else "weakness",
            key=key_good if better else key_bad,
            params={"value": _pct(rate), "baseline": _pct(base), "k": k, "n": n},
            score=min(1.0, effect * 2 + distance),
            sample=n,
            evidence=evidence,
            numbers=[_pct(rate), _pct(base), k, n],
        )
    )


def match_insights(
    stats: dict[str, Any], baseline: list[dict[str, Any]], limit: int = 6
) -> list[dict[str, Any]]:
    """Insights for one match. `baseline` = stats of the other matches of the season."""
    out: list[Insight] = []
    own, opp = stats["own"], stats["opponent"]
    base = baseline if len(baseline) >= MIN_BASELINE_MATCHES else []

    if base:
        bk, bn = _baseline_rate(base, "own", "goals", "shots")
        _vs_baseline(
            out,
            ident="shooting",
            k=own["goals"],
            n=own["shots"],
            bk=bk,
            bn=bn,
            higher_is_better=True,
            key_good="insights.shooting_above",
            key_bad="insights.shooting_below",
            min_n=MIN_SHOTS,
            evidence={"side": "own", "type": "shot"},
        )
        bk = sum(int(b["own"]["saves"]) for b in base)
        bn = sum(int(b["own"]["saves"]) + int(b["own"]["goals_against"]) for b in base)
        _vs_baseline(
            out,
            ident="saves",
            k=own["saves"],
            n=own["saves"] + own["goals_against"],
            bk=bk,
            bn=bn,
            higher_is_better=True,
            key_good="insights.saves_above",
            key_bad="insights.saves_below",
            min_n=MIN_SHOTS,
            evidence={"side": "opponent", "type": "shot", "outcome": "save"},
        )
        avg_to = sum(int(b["own"]["turnovers"]) for b in base) / len(base)
        if own["turnovers"] >= max(6, avg_to * 1.4) and own["turnovers"] - avg_to >= 3:
            top = max(own["turnovers_by_type"].items(), key=lambda kv: kv[1], default=("other", 0))
            out.append(
                Insight(
                    id="turnovers",
                    kind="weakness",
                    key="insights.turnovers_high",
                    params={
                        "value": own["turnovers"],
                        "baseline": round(avg_to, 1),
                        "type": top[0],
                        "type_count": top[1],
                    },
                    score=min(1.0, (own["turnovers"] - avg_to) / max(avg_to, 1) * 0.8),
                    sample=own["turnovers"],
                    evidence={"side": "own", "type": "turnover"},
                    numbers=[own["turnovers"], round(avg_to, 1), top[1]],
                )
            )

    # 7 m conversion
    if own["seven_m_shots"] >= MIN_SEVEN_M:
        k, n = own["seven_m_goals"], own["seven_m_shots"]
        rate = k / n
        if rate <= 0.5:
            out.append(
                Insight(
                    "seven_m",
                    "weakness",
                    "insights.seven_m_low",
                    {"k": k, "n": n, "value": _pct(rate)},
                    min(1.0, (0.75 - rate) * 1.5),
                    n,
                    {"side": "own", "type": "shot", "zone": "penalty"},
                    [k, n, _pct(rate)],
                )
            )

    # weakest and strongest own shot zone against the team's average in this match
    if own["shots"] >= MIN_SHOTS:
        avg = own["goals"] / own["shots"]
        for zone, z in own["zones"].items():
            if zone in ("penalty", "fast_break") or z["shots"] < MIN_ZONE_SHOTS:
                continue
            lo, hi = wilson(z["goals"], z["shots"])
            if hi < avg - 0.05:
                out.append(
                    Insight(
                        f"zone_{zone}",
                        "weakness",
                        "insights.zone_weak",
                        {"zone": zone, "k": z["goals"], "n": z["shots"], "avg": _pct(avg)},
                        min(1.0, (avg - z["goals"] / z["shots"]) * 1.5),
                        z["shots"],
                        {"side": "own", "type": "shot", "zone": zone},
                        [z["goals"], z["shots"], _pct(avg)],
                    )
                )
            elif lo > avg + 0.05:
                out.append(
                    Insight(
                        f"zone_{zone}",
                        "strength",
                        "insights.zone_strong",
                        {"zone": zone, "k": z["goals"], "n": z["shots"], "avg": _pct(avg)},
                        min(1.0, (z["goals"] / z["shots"] - avg) * 1.5),
                        z["shots"],
                        {"side": "own", "type": "shot", "zone": zone},
                        [z["goals"], z["shots"], _pct(avg)],
                    )
                )

    # where we concede: one goal zone with a large share of the goals against
    conceded = {z: v["goals"] for z, v in opp["goal_zones"].items()}
    total_c = sum(conceded.values())
    if total_c >= 6:
        zone, g = max(conceded.items(), key=lambda kv: kv[1])
        if g / total_c >= 0.35:
            out.append(
                Insight(
                    "conceded_zone",
                    "weakness",
                    "insights.conceded_zone",
                    {"zone": zone, "k": g, "n": total_c, "value": _pct(g / total_c)},
                    min(1.0, g / total_c),
                    total_c,
                    {"side": "opponent", "type": "shot", "outcome": "goal", "goal_zone": zone},
                    [g, total_c, _pct(g / total_c)],
                )
            )

    # opponent fast breaks
    if opp["fast_break_goals"] >= 4:
        out.append(
            Insight(
                "fast_breaks_against",
                "weakness",
                "insights.fast_breaks_against",
                {"value": opp["fast_break_goals"]},
                min(1.0, opp["fast_break_goals"] / 10),
                opp["fast_break_goals"],
                {"side": "opponent", "zone": "fast_break", "outcome": "goal"},
                [opp["fast_break_goals"]],
            )
        )

    # situations: powerplay / shorthanded efficiency
    pp = own["by_situation"].get("powerplay")
    if pp and pp["shots"] >= MIN_ZONE_SHOTS and (pp["pct"] or 0) < 0.4:
        out.append(
            Insight(
                "powerplay",
                "weakness",
                "insights.powerplay_weak",
                {"k": pp["goals"], "n": pp["shots"], "value": _pct(pp["pct"])},
                0.5,
                pp["shots"],
                {"side": "own", "type": "shot"},
                [pp["goals"], pp["shots"], _pct(pp["pct"])],
            )
        )

    # timeline: droughts and opponent runs
    drought = stats["timeline"]["longest_own_drought_s"]["seconds"]
    if drought >= 480:
        out.append(
            Insight(
                "drought",
                "weakness",
                "insights.drought",
                {"minutes": round(drought / 60)},
                min(1.0, drought / 1200),
                1,
                {"side": "own", "type": "shot"},
                [round(drought / 60)],
            )
        )
    run = stats["timeline"]["best_run"].get("opponent", {}).get("goals", 0)
    if run >= 4:
        out.append(
            Insight(
                "opponent_run",
                "weakness",
                "insights.opponent_run",
                {"goals": run},
                min(1.0, run / 8),
                run,
                {"side": "opponent", "type": "shot", "outcome": "goal"},
                [run],
            )
        )
    own_run = stats["timeline"]["best_run"].get("own", {}).get("goals", 0)
    if own_run >= 4:
        out.append(
            Insight(
                "own_run",
                "strength",
                "insights.own_run",
                {"goals": own_run},
                min(1.0, own_run / 8),
                own_run,
                {"side": "own", "type": "shot", "outcome": "goal"},
                [own_run],
            )
        )

    # goalkeepers with enough shots faced
    for k in (stats.get("goalkeepers") or {}).values():
        if k["side"] != "own" or k["faced"] < MIN_KEEPER_FACED or k.get("gsax") is None:
            continue
        if k["gsax"] >= 2 or k["gsax"] <= -2:
            good = k["gsax"] > 0
            out.append(
                Insight(
                    f"keeper_{k.get('player_id') or k.get('number') or 'u'}",
                    "strength" if good else "weakness",
                    "insights.keeper_good" if good else "insights.keeper_bad",
                    {
                        "player_id": k.get("player_id"),
                        "number": k.get("number"),
                        "saves": k["saves"],
                        "faced": k["faced"],
                        "gsax": k["gsax"],
                    },
                    min(1.0, abs(k["gsax"]) / 5),
                    k["faced"],
                    {"side": "opponent", "type": "shot"},
                    [k["saves"], k["faced"], abs(k["gsax"]), k["gsax"]],
                )
            )

    # players: efficient scorers and wasteful shooters
    for p in stats["players"].values():
        if p["side"] != "own" or p["shots"] < MIN_PLAYER_SHOTS:
            continue
        rate = p["goals"] / p["shots"]
        who = {"player_id": p.get("player_id"), "number": p.get("number")}
        ev = {"side": "own", "type": "shot"} | (
            {"player_id": p["player_id"]} if p.get("player_id") else {"number": p.get("number")}
        )
        if p["goals"] >= 5 and rate >= 0.7:
            out.append(
                Insight(
                    f"player_good_{p.get('player_id') or p.get('number')}",
                    "strength",
                    "insights.player_efficient",
                    {**who, "k": p["goals"], "n": p["shots"], "value": _pct(rate)},
                    min(1.0, rate - 0.3),
                    p["shots"],
                    ev,
                    [p["goals"], p["shots"], _pct(rate)],
                )
            )
        elif rate <= 0.3:
            out.append(
                Insight(
                    f"player_bad_{p.get('player_id') or p.get('number')}",
                    "weakness",
                    "insights.player_inefficient",
                    {**who, "k": p["goals"], "n": p["shots"], "value": _pct(rate)},
                    min(1.0, 0.6 - rate),
                    p["shots"],
                    ev,
                    [p["goals"], p["shots"], _pct(rate)],
                )
            )

    out.sort(key=lambda i: (-i.score, i.id))
    return [i.to_dict() for i in out[:limit]]

"""Season themes (SPEC 7.9, "Was sich wiederholt"): what keeps coming back across matches.

A theme is a finding of the match insights (same rule, same zone) that fires in at least
`MIN_MATCHES` matches with video, or a goal-against position that takes a large share of the goals
conceded in at least that many matches. Every theme carries one value per match with video (also
where it did not fire, so the series shows the trend) and the event filter of its scenes. Nothing
is said with fewer than two matches with video.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from handball_metrics.stats import POSITIONS

MIN_MATCHES = 2
MIN_CONCEDED = 6  # goals against in a match before a position share means anything
POSITION_SHARE = 0.3
THEMES_VERSION = "themes-1"


@dataclass
class MatchInput:
    match_id: str
    stats: dict[str, Any]
    insights: list[dict[str, Any]]


def _ratio(k: float, n: float) -> float | None:
    return round(k / n, 3) if n else None


def _value(theme: str, params: dict[str, Any], stats: dict[str, Any]) -> float | None:
    """The figure behind a theme in one match, from its stats (None when the match has no base)."""
    own, opp = stats["own"], stats["opponent"]
    if theme == "shooting":
        return _ratio(own["goals"], own["shots"])
    if theme == "saves":
        return _ratio(own["saves"], own["saves"] + own["goals_against"])
    if theme == "turnovers":
        return float(own["turnovers"])
    if theme == "seven_m":
        return _ratio(own["seven_m_goals"], own["seven_m_shots"])
    if theme.startswith("zone_"):
        z = own["zones"].get(theme.removeprefix("zone_"))
        return _ratio(z["goals"], z["shots"]) if z else None
    if theme.startswith("conceded_zone_"):
        zone = theme.removeprefix("conceded_zone_")
        total = sum(v["goals"] for v in opp["goal_zones"].values())
        return _ratio(opp["goal_zones"].get(zone, {}).get("goals", 0), total)
    if theme.startswith("conceded_position_"):
        pos = theme.removeprefix("conceded_position_")
        total = own["goals_against"]
        return _ratio(opp.get("positions", {}).get(pos, {}).get("goals", 0), total)
    if theme == "fast_breaks_against":
        return float(opp["fast_break_goals"])
    if theme == "powerplay":
        pp = own["by_situation"].get("powerplay")
        return _ratio(int(pp["goals"]), int(pp["shots"])) if pp else None
    if theme == "drought":
        return round(float(stats["timeline"]["longest_own_drought_s"]["seconds"]) / 60, 1)
    if theme == "opponent_run":
        return float(stats["timeline"]["best_run"].get("opponent", {}).get("goals", 0))
    if theme == "own_run":
        return float(stats["timeline"]["best_run"].get("own", {}).get("goals", 0))
    v = params.get("value")
    return float(v) if isinstance(v, int | float) else None


def _theme_id(item: dict[str, Any]) -> str:
    # the conceded goal zone is part of the finding: the top left corner is another theme
    if item["id"] == "conceded_zone":
        return f"conceded_zone_{item['params'].get('zone')}"
    return str(item["id"])


def _positions_fired(stats: dict[str, Any]) -> list[dict[str, Any]]:
    """A position that takes a large share of the goals conceded in one match."""
    opp = stats["opponent"]
    total = stats["own"]["goals_against"]
    if total < MIN_CONCEDED:
        return []
    out = []
    for pos in POSITIONS:
        p = opp.get("positions", {}).get(pos)
        if p and p["goals"] / total >= POSITION_SHARE:
            out.append(
                {
                    "id": f"conceded_position_{pos}",
                    "kind": "weakness",
                    "key": "themes.conceded_position",
                    "params": {"position": pos, "k": p["goals"], "n": total},
                    "score": min(1.0, p["goals"] / total),
                    "evidence": {
                        "side": "opponent",
                        "type": "shot",
                        "outcome": "goal",
                        "zones": p["zones"],
                    },
                }
            )
    return out


def season_themes(matches: list[MatchInput], limit: int = 3) -> list[dict[str, Any]]:
    """Themes over the matches with video of a season, the most persistent first."""
    if len(matches) < MIN_MATCHES:
        return []
    fired: dict[str, dict[str, dict[str, Any]]] = {}
    for m in matches:
        for item in [*m.insights, *_positions_fired(m.stats)]:
            if item.get("kind") == "info":
                continue
            fired.setdefault(_theme_id(item), {})[m.match_id] = item
    themes = []
    for theme, by_match in fired.items():
        if len(by_match) < MIN_MATCHES:
            continue
        sample = next(iter(by_match.values()))
        last = list(by_match.values())[-1]
        themes.append(
            {
                "id": theme,
                "kind": sample["kind"],
                "key": sample["key"],
                "params": last["params"],
                "matches": len(by_match),
                "of": len(matches),
                "score": round(sum(i["score"] for i in by_match.values()) / len(by_match), 3),
                "per_match": [
                    {
                        "match_id": m.match_id,
                        "fired": m.match_id in by_match,
                        "value": _value(theme, by_match.get(m.match_id, last)["params"], m.stats),
                        "evidence": by_match.get(m.match_id, last)["evidence"],
                    }
                    for m in matches
                ],
            }
        )
    # the most persistent first, weaknesses before strengths at equal persistence, then strength
    themes.sort(key=lambda t: (-t["matches"], t["kind"] != "weakness", -t["score"]))
    return themes[:limit]

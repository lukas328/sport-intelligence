"""Evaluation set of the data assistant (addendum 01, 5.1): a deterministic team season and 62
questions with expected answers.

Expected values are computed directly from the raw event dicts below (plain Python, independent of
`handball_metrics.query`). Each question also carries the tool plan a correct model would follow:
CI replays that plan with `ScriptedModel` (tools, validator and answer path, no network); the live
run (`ml/eval/assistant.py`) asks the real model and scores its answers against the same values.
"""

from __future__ import annotations

import json
import random
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from handball_api.core.assistant_llm import ModelTurn, Usage
from handball_court.zones import shot_zone
from handball_metrics.xg import expected_goal

OPPONENTS = ["TV Muster", "HC Beispiel", "SG Probe", "TSV Test"]
NUMBERS = [2, 4, 7, 9, 11, 13, 17, 23]
PLAYS = ["Kreuzung links", "Stoss Mitte"]
SPOTS = {
    "wing_left": (38.3, 18.6),
    "wing_right": (38.3, 1.4),
    "back_left": (28.0, 15.0),
    "back_centre": (29.0, 10.0),
    "back_right": (28.5, 4.5),
    "circle_centre": (34.5, 10.0),
    "half_centre": (32.0, 10.5),
}
GOAL_ZONES = ["TL", "TC", "TR", "ML", "MC", "MR", "BL", "BC", "BR"]


@dataclass
class Match:
    index: int
    opponent: str
    day: date
    events: list[dict[str, Any]] = field(default_factory=list)
    video: bool = False

    @property
    def score(self) -> tuple[int, int]:
        own = sum(1 for e in self.events if _goal(e) and e["side"] == "own")
        opp = sum(1 for e in self.events if _goal(e) and e["side"] == "opponent")
        return own, opp


def _goal(e: dict[str, Any]) -> bool:
    return bool(e["type"] == "shot" and e["outcome"] == "goal")


def build() -> list[Match]:
    rnd = random.Random(5110)
    out = []
    start = date(2026, 9, 5)
    for i in range(8):
        m = Match(i, OPPONENTS[i % 4], start + timedelta(days=7 * i), video=i >= 5)
        for k in range(70):
            period = 1 if k < 35 else 2
            clock = (period - 1) * 1800 + (k % 35) * 50 + rnd.randint(0, 40)
            side = "own" if rnd.random() < 0.5 else "opponent"
            r = rnd.random()
            e: dict[str, Any] = {
                "type": "shot",
                "side": side,
                "period": period,
                "clock_s": float(clock),
                "t_ms": (clock * 1000 + 5000) if m.video else None,
                "number": None,
                "x": None,
                "y": None,
                "outcome": None,
                "shot_type": None,
                "goal_zone": None,
                "turnover_type": None,
                "play": None,
            }
            if r < 0.12:
                e.update(type="turnover", turnover_type=rnd.choice(["bad_pass", "steps"]))
            elif r < 0.16:
                e.update(type="suspension_2min")
            elif r < 0.19 and side == "own":
                e.update(type="timeout")
            else:
                kind = rnd.choices(
                    [*SPOTS, "penalty", "fast_break"], weights=[12, 12, 15, 15, 15, 12, 8, 7, 6]
                )[0]
                if kind == "penalty":
                    e.update(x=33.0, y=10.0, shot_type="penalty")
                elif kind == "fast_break":
                    e.update(x=34.0, y=10.0, shot_type="fast_break")
                else:
                    bx, by = SPOTS[kind]
                    e.update(x=bx, y=by, shot_type="wing" if kind.startswith("wing") else None)
                e["outcome"] = rnd.choices(
                    ["goal", "save", "miss", "post", "blocked"], weights=[55, 25, 10, 5, 5]
                )[0]
                if e["outcome"] in ("goal", "save"):
                    e["goal_zone"] = rnd.choice(GOAL_ZONES)
                e["number"] = rnd.choice(NUMBERS) if side == "own" else rnd.randint(2, 30)
                if side == "own" and kind in ("back_left", "circle_centre") and rnd.random() < 0.5:
                    e["play"] = PLAYS[0] if kind == "back_left" else PLAYS[1]
            m.events.append(e)
        out.append(m)
    return out


MATCHES = build()


# ---- independent expectations ----------------------------------------------------------------


def evs(last: int | None = None, opponent: str | None = None, **conds: Any) -> list[dict[str, Any]]:
    ms = sorted(MATCHES, key=lambda m: m.day, reverse=True)
    if opponent:
        ms = [m for m in ms if m.opponent == opponent]
    if last:
        ms = ms[:last]
    out = []
    for m in ms:
        for e in m.events:
            if all(_cond(e, k, v) for k, v in conds.items()):
                out.append({**e, "match": m})
    return out


def _cond(e: dict[str, Any], key: str, value: Any) -> bool:
    if key == "zone":
        return bool(_zone(e) == value)
    if key == "minute_from":
        return bool(int(e["clock_s"] // 60) + 1 >= value)
    if key == "minute_to":
        return bool(int(e["clock_s"] // 60) + 1 <= value)
    return bool(e.get(key) == value)


def _zone(e: dict[str, Any]) -> str | None:
    if e["type"] != "shot":
        return None
    if e["shot_type"] == "penalty":
        return "penalty"
    return shot_zone(e["x"], e["y"], fast_break=e["shot_type"] == "fast_break")


def _counter(**conds: Any) -> Callable[[], float]:
    return lambda: float(count(**conds))


def _shooter(**conds: Any) -> Callable[[], float]:
    return lambda: shooting(**conds)


def pct(goals: int, shots: int) -> float:
    return round(goals / shots, 3)


def shooting(**conds: Any) -> float:
    shots = evs(type="shot", **conds)
    return pct(sum(1 for e in shots if e["outcome"] == "goal"), len(shots))


def count(**conds: Any) -> int:
    return len(evs(**conds))


def after_timeout(side: str, outcome: str | None, window: int = 120) -> list[dict[str, Any]]:
    out = []
    for m in MATCHES:
        tos = [(e["period"], e["clock_s"]) for e in m.events if e["type"] == "timeout"]
        for e in m.events:
            if e["type"] != "shot" or e["side"] != side:
                continue
            if outcome and e["outcome"] != outcome:
                continue
            if any(p == e["period"] and 0 < e["clock_s"] - c <= window for p, c in tos):
                out.append(e)
    return out


# ---- questions -----------------------------------------------------------------------------------

Step = tuple[str, dict[str, Any] | Callable[[list[dict[str, Any]]], dict[str, Any]]]


@dataclass
class Question:
    id: str
    text: str
    plan: list[Step]
    # picks the answer values from the tool results (what a correct model would report)
    pick: Callable[[list[dict[str, Any]]], list[float]]
    expect: Callable[[], list[float]]
    answerable: bool = True
    tolerance: float = 0.001


def agg(metric: str, group_by: str | None = None, **f: Any) -> Step:
    args: dict[str, Any] = {"metric": metric, "filter": f}
    if group_by:
        args["group_by"] = group_by
    return ("aggregate_metric", args)


def value(i: int = -1) -> Callable[[list[dict[str, Any]]], list[float]]:
    return lambda rs: [rs[i]["value"]]


def qa(
    id_: str, text: str, step: Step, expect: Callable[[], float], tol: float = 0.001
) -> Question:
    return Question(id_, text, [step], value(), lambda: [expect()], tolerance=tol)


def _zone_label(z: str) -> str:
    return {
        "wing_right": "Rechtsaussen",
        "wing_left": "Linksaussen",
        "circle_centre": "den Kreis",
        "back_centre": "Rückraum Mitte",
        "back_left": "Rückraum links",
        "back_right": "Rückraum rechts",
        "penalty": "7 m",
    }[z]


def _xg(side: str) -> float:
    return round(
        sum(expected_goal(e["x"], e["y"], e["shot_type"]) for e in evs(type="shot", side=side)),
        1,
    )


def _top_scorer() -> list[float]:
    goals: dict[int, int] = {}
    for e in evs(type="shot", side="own", outcome="goal"):
        goals[e["number"]] = goals.get(e["number"], 0) + 1
    best = sorted(goals.items(), key=lambda kv: (-kv[1], str(kv[0])))[0]
    return [float(best[0]), float(best[1])]


def _per_half() -> list[float]:
    return [
        float(count(type="shot", side="own", outcome="goal", period=1)),
        float(count(type="shot", side="own", outcome="goal", period=2)),
    ]


def _halves(rs: list[dict[str, Any]]) -> list[float]:
    groups = {g["key"]: g["value"] for g in rs[-1]["groups"]}
    return [groups["1"], groups["2"]]


def _newest() -> Match:
    return max(MATCHES, key=lambda m: m.day)


def _ids_of(rs: list[dict[str, Any]], opponent: str) -> list[str]:
    return [m["match_id"] for m in rs[0]["matches"] if m["opponent"] == opponent]


def _plays(name: str, key: str) -> Callable[[list[dict[str, Any]]], list[float]]:
    return lambda rs: [next(p[key] for p in rs[-1]["plays"] if p["name"] == name)]


def _play_expect(name: str) -> tuple[int, int]:
    shots = [e for e in evs(type="shot", side="own") if e["play"] == name]
    return sum(1 for e in shots if e["outcome"] == "goal"), len(shots)


def _best_play() -> list[float]:
    best = max(PLAYS, key=lambda n: (_play_expect(n)[0], n))
    return [float(_play_expect(best)[0])]


def _last_vs_before() -> list[float]:
    ms = sorted(MATCHES, key=lambda m: m.day, reverse=True)

    def rate(sel: list[Match]) -> float:
        shots = [e for m in sel for e in m.events if e["type"] == "shot" and e["side"] == "own"]
        return pct(sum(1 for e in shots if e["outcome"] == "goal"), len(shots))

    return [rate(ms[:4]), rate(ms[4:])]


def _compare_matches(rs: list[dict[str, Any]]) -> dict[str, Any]:
    ids = [m["match_id"] for m in rs[0]["matches"]]
    return {
        "metric": "shooting_pct",
        "a": {"label": "letzte 4", "filter": {"side": "own", "match_ids": ids[:4]}},
        "b": {"label": "4 davor", "filter": {"side": "own", "match_ids": ids[4:8]}},
    }


def _clips(rs: list[dict[str, Any]]) -> dict[str, Any]:
    return {"event_ids": [e["event_id"] for e in rs[0]["events"] if e["has_video"]][:5]}


def _unanswerable(id_: str, text: str, plan: list[Step] | None = None) -> Question:
    return Question(id_, text, plan or [], lambda rs: [], lambda: [], answerable=False)


QUESTIONS: list[Question] = [
    qa(
        "shoot_last5",
        "Wie hoch war unsere Wurfquote in den letzten 5 Spielen?",
        agg("shooting_pct", side="own", last_n_matches=5),
        lambda: shooting(side="own", last=5),
    ),
    qa(
        "shoot_all",
        "Wie ist unsere Wurfquote über die ganze Saison?",
        agg("shooting_pct", side="own"),
        lambda: shooting(side="own"),
    ),
    qa(
        "goals_all",
        "Wie viele Tore haben wir insgesamt erzielt?",
        agg("goals", side="own"),
        lambda: count(type="shot", side="own", outcome="goal"),
    ),
    qa(
        "against_all",
        "Wie viele Gegentore haben wir bekommen?",
        agg("goals", side="opponent"),
        lambda: count(type="shot", side="opponent", outcome="goal"),
    ),
    *[
        qa(
            f"own_{z}",
            f"Wie viele Tore haben wir über {_zone_label(z)} erzielt?",
            agg("goals", side="own", zone=z),
            _counter(type="shot", side="own", outcome="goal", zone=z),
        )
        for z in ("wing_right", "wing_left", "circle_centre", "back_centre")
    ],
    *[
        qa(
            f"against_{z}_last5",
            f"Wie viele Gegentore gab es über {_zone_label(z)} in den letzten 5 Spielen?",
            agg("goals", side="opponent", zone=z, last_n_matches=5),
            _counter(type="shot", side="opponent", outcome="goal", zone=z, last=5),
        )
        for z in ("wing_right", "wing_left", "circle_centre", "penalty")
    ],
    qa(
        "keeper_pct",
        "Wie hoch ist die Paradenquote unseres Torhüters?",
        agg("save_pct", side="opponent"),
        lambda: pct(
            count(type="shot", side="opponent", outcome="save"),
            count(type="shot", side="opponent", outcome="save")
            + count(type="shot", side="opponent", outcome="goal"),
        ),
    ),
    qa(
        "keeper_saves_last3",
        "Wie viele Paraden hatte unser Torhüter in den letzten 3 Spielen?",
        agg("saves", side="opponent", last_n_matches=3),
        lambda: count(type="shot", side="opponent", outcome="save", last=3),
    ),
    qa(
        "seven_own",
        "Wie gut verwandeln wir 7-Meter?",
        agg("seven_m_pct", side="own"),
        lambda: pct(
            count(type="shot", side="own", shot_type="penalty", outcome="goal"),
            count(type="shot", side="own", shot_type="penalty"),
        ),
    ),
    qa(
        "seven_opp",
        "Wie gut verwandelt der Gegner seine 7-Meter gegen uns?",
        agg("seven_m_pct", side="opponent"),
        lambda: pct(
            count(type="shot", side="opponent", shot_type="penalty", outcome="goal"),
            count(type="shot", side="opponent", shot_type="penalty"),
        ),
    ),
    qa(
        "fast_breaks",
        "Wie viele Gegenstosstore haben wir gemacht?",
        agg("fast_break_goals", side="own"),
        lambda: count(type="shot", side="own", shot_type="fast_break", outcome="goal"),
    ),
    qa(
        "turnovers",
        "Wie viele Ballverluste hatten wir?",
        agg("turnovers", side="own"),
        lambda: count(type="turnover", side="own"),
    ),
    qa(
        "turnovers_last3",
        "Wie viele Ballverluste hatten wir in den letzten 3 Spielen?",
        agg("turnovers", side="own", last_n_matches=3),
        lambda: count(type="turnover", side="own", last=3),
    ),
    qa(
        "suspensions",
        "Wie viele Zeitstrafen haben wir bekommen?",
        agg("suspensions", side="own"),
        lambda: count(type="suspension_2min", side="own"),
    ),
    *[
        qa(
            f"goals_no{n}",
            f"Wie viele Tore hat Nummer {n} geworfen?",
            agg("goals", side="own", number=n),
            _counter(type="shot", side="own", outcome="goal", number=n),
        )
        for n in (7, 9, 11, 23)
    ],
    qa(
        "shoot_no9",
        "Wie ist die Wurfquote von Nr. 9?",
        agg("shooting_pct", side="own", number=9),
        lambda: shooting(side="own", number=9),
    ),
    Question(
        "top_scorer",
        "Wer ist unser bester Torschütze?",
        [agg("goals", "number", side="own", type="shot")],
        lambda rs: [float(rs[-1]["groups"][0]["key"]), rs[-1]["groups"][0]["value"]],
        _top_scorer,
    ),
    qa(
        "timeout_pct",
        "Wie oft treffen wir nach einem Timeout?",
        agg("shooting_pct", side="own", after_timeout_s=120),
        lambda: pct(len(after_timeout("own", "goal")), len(after_timeout("own", None))),
    ),
    qa(
        "timeout_goals",
        "Wie viele Tore haben wir in den zwei Minuten nach unseren Timeouts erzielt?",
        agg("goals", side="own", after_timeout_s=120),
        lambda: len(after_timeout("own", "goal")),
    ),
    Question(
        "halves_compare",
        "Werfen wir in der zweiten Halbzeit besser als in der ersten?",
        [
            (
                "compare_periods",
                {
                    "metric": "shooting_pct",
                    "a": {"label": "1. HZ", "filter": {"side": "own", "period": 1}},
                    "b": {"label": "2. HZ", "filter": {"side": "own", "period": 2}},
                },
            )
        ],
        lambda rs: [rs[-1]["a"]["value"], rs[-1]["b"]["value"]],
        lambda: [shooting(side="own", period=1), shooting(side="own", period=2)],
    ),
    Question(
        "last4_vs_before",
        "Ist unsere Wurfquote in den letzten 4 Spielen besser als in den 4 davor?",
        [("list_matches", {"last_n": 8}), ("compare_periods", _compare_matches)],
        lambda rs: [rs[-1]["a"]["value"], rs[-1]["b"]["value"]],
        _last_vs_before,
    ),
    *[
        qa(
            f"shoot_vs_{o.split()[1].lower()}",
            f"Wie war unsere Wurfquote gegen {o}?",
            agg("shooting_pct", side="own", opponent=o),
            _shooter(side="own", opponent=o),
        )
        for o in OPPONENTS
    ],
    qa(
        "against_probe",
        "Wie viele Gegentore haben wir gegen SG Probe kassiert?",
        agg("goals", side="opponent", opponent="SG Probe"),
        lambda: count(type="shot", side="opponent", outcome="goal", opponent="SG Probe"),
    ),
    Question(
        "n_matches",
        "Wie viele Spiele sind erfasst?",
        [("list_matches", {})],
        lambda rs: [rs[-1]["total_matches"]],
        lambda: [len(MATCHES)],
    ),
    Question(
        "last_result",
        "Wie ist unser letztes Spiel ausgegangen?",
        [("list_matches", {"last_n": 1})],
        lambda rs: [rs[-1]["matches"][0]["score_own"], rs[-1]["matches"][0]["score_opponent"]],
        lambda: list(_newest().score),
    ),
    qa(
        "goals_last10min",
        "Wie viele Tore haben wir in den letzten 10 Minuten der Spiele erzielt?",
        agg("goals", side="own", minute_from=51),
        lambda: count(type="shot", side="own", outcome="goal", minute_from=51),
    ),
    qa(
        "against_first10min",
        "Wie viele Gegentore gab es in den ersten 10 Minuten?",
        agg("goals", side="opponent", minute_to=10),
        lambda: count(type="shot", side="opponent", outcome="goal", minute_to=10),
    ),
    Question(
        "goals_per_half",
        "Wie viele Tore erzielen wir pro Halbzeit?",
        [agg("goals", "period", side="own")],
        _halves,
        _per_half,
    ),
    qa(
        "xg_own",
        "Wie viele Tore wären aus unseren Wurfpositionen zu erwarten gewesen?",
        agg("xg", side="own"),
        lambda: _xg("own"),
        tol=0.15,
    ),
    qa(
        "xg_opp",
        "Wie hoch ist der xG-Wert des Gegners gegen uns?",
        agg("xg", side="opponent"),
        lambda: _xg("opponent"),
        tol=0.15,
    ),
    qa(
        "goals_tl",
        "Wie viele Tore haben wir ins obere linke Eck geworfen?",
        agg("goals", side="own", goal_zone="TL"),
        lambda: count(type="shot", side="own", outcome="goal", goal_zone="TL"),
    ),
    qa(
        "against_br",
        "Wie viele Gegentore fielen unten rechts?",
        agg("goals", side="opponent", goal_zone="BR"),
        lambda: count(type="shot", side="opponent", outcome="goal", goal_zone="BR"),
    ),
    qa(
        "misses",
        "Wie viele Fehlwürfe hatten wir?",
        agg("shots", side="own", outcome="miss"),
        lambda: count(type="shot", side="own", outcome="miss"),
    ),
    qa(
        "posts",
        "Wie oft haben wir den Pfosten getroffen?",
        agg("shots", side="own", outcome="post"),
        lambda: count(type="shot", side="own", outcome="post"),
    ),
    qa(
        "blocked",
        "Wie viele unserer Würfe wurden geblockt?",
        agg("shots", side="own", outcome="blocked"),
        lambda: count(type="shot", side="own", outcome="blocked"),
    ),
    qa(
        "shoot_back_centre",
        "Wie ist unsere Wurfquote aus dem Rückraum Mitte?",
        agg("shooting_pct", side="own", zone="back_centre"),
        lambda: shooting(side="own", zone="back_centre"),
    ),
    qa(
        "shoot_circle",
        "Wie oft treffen wir vom Kreis?",
        agg("shooting_pct", side="own", zone="circle_centre"),
        lambda: shooting(side="own", zone="circle_centre"),
    ),
    Question(
        "show_against_rw",
        "Zeig alle Gegentore über Rechtsaussen in den letzten 5 Spielen.",
        [
            (
                "query_events",
                {
                    "filter": {
                        "side": "opponent",
                        "type": "shot",
                        "outcome": "goal",
                        "zone": "wing_right",
                        "last_n_matches": 5,
                    }
                },
            )
        ],
        lambda rs: [rs[-1]["count"]],
        lambda: [count(type="shot", side="opponent", outcome="goal", zone="wing_right", last=5)],
    ),
    Question(
        "clips_no7",
        "Zeig mir die Tore von Nummer 7 im Video.",
        [
            (
                "query_events",
                {
                    "filter": {"side": "own", "type": "shot", "outcome": "goal", "number": 7},
                    "limit": 30,
                },
            ),
            ("get_clips", _clips),
        ],
        lambda rs: [rs[0]["count"]],
        lambda: [count(type="shot", side="own", outcome="goal", number=7)],
    ),
    Question(
        "best_play",
        "Welcher Spielzug bringt uns die meisten Tore?",
        [("find_plays", {})],
        lambda rs: [max(p["goals"] for p in rs[-1]["plays"])],
        _best_play,
    ),
    Question(
        "play_crossing",
        "Wie erfolgreich ist der Spielzug Kreuzung links?",
        [("find_plays", {})],
        _plays(PLAYS[0], "shooting_pct"),
        lambda: [pct(*_play_expect(PLAYS[0]))],
    ),
    Question(
        "play_stoss_shots",
        "Wie oft haben wir Stoss Mitte gespielt?",
        [("find_plays", {})],
        _plays(PLAYS[1], "shots"),
        lambda: [float(_play_expect(PLAYS[1])[1])],
    ),
    _unanswerable(
        "play_vs_51",
        "Welcher Spielzug funktioniert gegen eine 5-1-Abwehr?",
        [("find_plays", {"opponent_formation": "5-1"})],
    ),
    _unanswerable("speed", "Wie schnell läuft Nummer 7?"),
    _unanswerable("spectators", "Wie viele Zuschauer waren beim letzten Spiel?"),
    _unanswerable("by_name", "Wie viele Tore hat Lena Muster geworfen?"),
    _unanswerable("weather", "Wie ist unsere Wurfquote bei Regen?"),
    _unanswerable("salary", "Was verdient unser Trainer?"),
    _unanswerable("future", "Wie viele Tore werden wir im nächsten Spiel werfen?"),
    qa(
        "opp_turnovers",
        "Wie viele Ballverluste hatte der Gegner?",
        agg("turnovers", side="opponent"),
        lambda: count(type="turnover", side="opponent"),
    ),
    qa(
        "opp_suspensions",
        "Wie viele Zeitstrafen bekam der Gegner?",
        agg("suspensions", side="opponent"),
        lambda: count(type="suspension_2min", side="opponent"),
    ),
    qa(
        "opp_no5",
        "Wie viele Tore hat die gegnerische Nummer 5 gegen uns geworfen?",
        agg("goals", side="opponent", number=5),
        lambda: count(type="shot", side="opponent", outcome="goal", number=5),
    ),
    Question(
        "insights_last",
        "Was sind die Erkenntnisse aus dem letzten Spiel?",
        [("list_insights", {})],
        lambda rs: [rs[-1]["baseline_matches"]],
        lambda: [len(MATCHES) - 1],
    ),
    qa(
        "keeper_rw",
        "Wie viele Würfe von Rechtsaussen hält unser Torhüter (Quote)?",
        agg("save_pct", side="opponent", zone="wing_right"),
        lambda: pct(
            count(type="shot", side="opponent", outcome="save", zone="wing_right"),
            count(type="shot", side="opponent", outcome="save", zone="wing_right")
            + count(type="shot", side="opponent", outcome="goal", zone="wing_right"),
        ),
    ),
    qa(
        "seven_goals_h2",
        "Wie viele 7-Meter-Tore haben wir in der zweiten Halbzeit gemacht?",
        agg("seven_m_goals", side="own", period=2),
        lambda: count(type="shot", side="own", shot_type="penalty", outcome="goal", period=2),
    ),
    qa(
        "shots_total",
        "Wie viele Würfe hatten wir insgesamt?",
        agg("shots", side="own"),
        lambda: count(type="shot", side="own"),
    ),
    qa(
        "opp_shots_last2",
        "Wie viele Würfe hatte der Gegner in den letzten 2 Spielen?",
        agg("shots", side="opponent", last_n_matches=2),
        lambda: count(type="shot", side="opponent", last=2),
    ),
    qa(
        "on_target",
        "Wie viele unserer Würfe gehen aufs Tor (Quote)?",
        agg("on_target_pct", side="own"),
        lambda: pct(
            count(type="shot", side="own", outcome="goal")
            + count(type="shot", side="own", outcome="save"),
            count(type="shot", side="own"),
        ),
    ),
]


# ---- scripted model ------------------------------------------------------------------------------


class ScriptedModel:
    """Follows a fixed tool plan, then answers with the values `pick` takes from the results."""

    model = "scripted"

    def __init__(self, q: Question, invent: bool = False) -> None:
        self.q, self.invent = q, invent

    async def respond(
        self, system: str, tools: list[dict[str, Any]], messages: list[dict[str, Any]]
    ) -> ModelTurn:
        results = []
        for m in messages:
            if m["role"] == "user" and isinstance(m["content"], list):
                for block in m["content"]:
                    if (
                        block.get("type") == "tool_result"
                        and not block.get("is_error")
                        and block.get("content") != "shown"
                    ):
                        results.append(json.loads(block["content"]))
        step = len(results)
        turn_usage = Usage(input_tokens=1000, output_tokens=100)
        if step < len(self.q.plan):
            name, args = self.q.plan[step]
            payload = args(results) if callable(args) else args
            block = {"type": "tool_use", "id": f"t{step}", "name": name, "input": payload}
            return ModelTurn([block], "tool_use", turn_usage, self.model, 5)
        if not self.q.answerable:
            answer: dict[str, Any] = {
                "answerable": False,
                "text": "Dazu habe ich keine Daten.",
                "suggestion": "Wie hoch war unsere Wurfquote in den letzten 5 Spielen?",
            }
        else:
            values = self.q.pick(results)
            shown = ", ".join(_fmt(v) for v in values)
            answer = {
                "answerable": True,
                "text": f"Wert: {shown}." + (" Dazu 4711 Extra." if self.invent else ""),
                "values": values,
                "sample_size": None,
                "event_ids": _first_ids(results),
            }
            self.invent = False  # the correction round gets an honest answer
        block = {"type": "tool_use", "id": f"f{step}", "name": "final_answer", "input": answer}
        return ModelTurn([block], "tool_use", turn_usage, self.model, 5)


def _fmt(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else str(v)


def _first_ids(results: list[dict[str, Any]]) -> list[str]:
    for r in results:
        if isinstance(r.get("events"), list) and r["events"]:
            return [e["event_id"] for e in r["events"][:3]]
        if r.get("example_event_ids"):
            return list(r["example_event_ids"][:3])
    return []


def score(answer: dict[str, Any], q: Question) -> bool:
    """A correct answer has the right answerability and contains every expected value."""
    if bool(answer.get("answerable")) != q.answerable:
        return False
    got = [float(v) for v in answer.get("values") or []]
    return all(any(abs(g - e) <= q.tolerance for g in got) for e in q.expect())

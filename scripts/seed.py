"""Demo data (BRIEF 15, docs/design/ux-reset/SPEC.md section 10): `make seed` against the running
stack (docker compose up, or scripts/local-stack.sh).

A club from the Zürichsee region that shows the product the way a coach would use it:

- Herren 1 with a confirmed squad (numbers, positions) and its kit (two colours, a pattern),
- three matches with video (synthetic footage through the real pipeline) and their events: about
  50 shots per side with places and goal corners, 7 m, turnovers, so each match has its three
  things, a shot map, goals conceded by position and 30 or more scenes,
- two older matches with a match report only (paper import),
- two themes that repeat over the matches with video (the right wing stays open, 7 m are missed),
- one collection made from the last match, and the opponents' colours.

Numbers are uneven and plausible; names are invented, places are real. Everything is marked as
demo. The videos are rendered by packages/vision (synthetic, not real footage).

    uv run python scripts/seed.py [--web http://localhost:3000]
"""

from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

EMAIL = "demo@handball-demo.ch"
PASSWORD = "demo-handball-2026"  # noqa: S105 (local demo account)
CLUB = "HC Zürichsee"
VIDEO_SECONDS = 60

# the squad of Herren 1: number, first name, last name, position, hand, birth year
SQUAD = [
    (1, "Andrin", "Gerber", "TW", "right", 1997),
    (12, "Silvan", "Huber", "TW", "right", 2001),
    (3, "Luca", "Brunner", "LA", "right", 2000),
    (21, "Nico", "Steiner", "LA", "right", 2003),
    (7, "Fabian", "Keller", "RL", "right", 1998),
    (17, "Dario", "Moser", "RL", "right", 2002),
    (9, "Simon", "Meier", "RM", "right", 1996),
    (14, "Gian", "Bühler", "RM", "right", 2004),
    (10, "Marco", "Frei", "RR", "left", 1999),
    (25, "Levin", "Kunz", "RR", "left", 2003),
    (5, "Elias", "Zürcher", "RA", "left", 2001),
    (19, "Jonas", "Roth", "RA", "left", 2005),
    (11, "Tim", "Baumann", "KM", "right", 1997),
    (22, "Noah", "Graf", "KM", "right", 2002),
]
YOUTH = [
    (1, "Lea", "Schmid", "TW"),
    (4, "Mia", "Weber", "LA"),
    (6, "Nina", "Meier", "RL"),
    (8, "Alina", "Huber", "RM"),
    (9, "Jana", "Keller", "RR"),
    (13, "Elena", "Frei", "RA"),
    (15, "Sara", "Gerber", "KM"),
    (18, "Laura", "Brunner", "RL"),
]

# where a shot comes from (attacked goal at x = 40, the court is 20 m wide; left is y > 10)
SPOTS: dict[str, list[tuple[float, float]]] = {
    "LA": [(38.2, 18.6), (37.6, 17.9), (38.6, 19.0)],
    "RA": [(38.3, 1.4), (37.7, 2.1), (38.6, 1.0)],
    "RL": [(30.6, 15.2), (31.2, 14.1), (29.8, 16.0)],
    "RM": [(30.0, 10.4), (30.8, 9.2), (29.4, 11.1)],
    "RR": [(30.6, 4.9), (31.1, 5.8), (29.9, 4.1)],
    "KM": [(34.6, 10.3), (34.2, 8.9), (34.9, 11.4)],
}
CORNERS = ["TL", "TC", "TR", "ML", "MC", "MR", "BL", "BC", "BR"]


class Client:
    def __init__(self, web: str) -> None:
        self.http = httpx.Client(base_url=web, timeout=60, headers={"origin": web})

    def _h(self) -> dict[str, str]:
        csrf = self.http.cookies.get("hb_csrf")
        return {"x-csrf-token": csrf} if csrf else {}

    def get(self, url: str) -> httpx.Response:
        return self.http.get(url)

    def post(self, url: str, **kw: Any) -> httpx.Response:
        r = self.http.post(url, headers=self._h(), **kw)
        if r.status_code >= 400:
            sys.exit(f"POST {url} -> {r.status_code} {r.text[:300]}")
        return r

    def patch(self, url: str, **kw: Any) -> httpx.Response:
        r = self.http.patch(url, headers=self._h(), **kw)
        if r.status_code >= 400:
            sys.exit(f"PATCH {url} -> {r.status_code} {r.text[:300]}")
        return r


def upload(c: Client, org: str, match: str, path: Path) -> None:
    size = path.stat().st_size
    up = c.post(
        f"/v1/orgs/{org}/matches/{match}/videos", json={"filename": "spiel.mp4", "size_bytes": size}
    ).json()
    vid, part = up["video"]["id"], up["part_size"]
    numbers = list(range(1, up["part_count"] + 1))
    urls = {
        u["number"]: u["url"]
        for u in c.post(f"/v1/orgs/{org}/videos/{vid}/parts", json={"numbers": numbers}).json()
    }
    parts = []
    with path.open("rb") as f:
        for n in numbers:
            r = httpx.put(urls[n], content=f.read(part), timeout=120)
            r.raise_for_status()
            parts.append({"number": n, "etag": r.headers["etag"].strip('"')})
    c.post(f"/v1/orgs/{org}/videos/{vid}/complete", json={"parts": parts})


def pick_weighted(rng: random.Random, weights: dict[str, float]) -> str:
    return rng.choices(list(weights), weights=list(weights.values()))[0]


def match_events(
    rng: random.Random,
    *,
    players: dict[str, list[str]],
    own_goals: int,
    opp_goals: int,
    own_misses: int,
    keeper_saves: int,
    seven_m: tuple[int, int],
    opp_from_right_wing: int,
    turnovers: int,
    keeper: str,
) -> list[dict[str, Any]]:
    """One match as events. `players` maps a position to roster player ids."""
    own_weights = {"LA": 0.13, "RL": 0.2, "RM": 0.17, "RR": 0.18, "RA": 0.12, "KM": 0.2}
    opp_weights = {"LA": 0.16, "RL": 0.2, "RM": 0.2, "RR": 0.16, "KM": 0.28}
    sevens_taken, sevens_scored = seven_m
    events: list[dict[str, Any]] = []

    def own_shot(outcome: str) -> dict[str, Any]:
        pos = pick_weighted(rng, own_weights)
        x, y = rng.choice(SPOTS[pos])
        e: dict[str, Any] = {
            "type": "shot",
            "side": "own",
            "outcome": outcome,
            "player_id": rng.choice(players[pos]),
            "x": round(x + rng.uniform(-0.4, 0.4), 1),
            "y": round(y + rng.uniform(-0.4, 0.4), 1),
        }
        if outcome in ("goal", "save"):
            e["goal_zone"] = rng.choice(CORNERS)
        return e

    for _ in range(own_goals - sevens_scored):
        events.append(own_shot("goal"))
    for _ in range(own_misses):
        events.append(own_shot(rng.choice(["save", "save", "save", "miss", "post", "blocked"])))
    for k in range(sevens_taken):
        events.append(
            {
                "type": "shot",
                "side": "own",
                "outcome": "goal" if k < sevens_scored else rng.choice(["save", "post"]),
                "shot_type": "penalty",
                "player_id": rng.choice(players["RR"] + players["RA"]),
                "goal_zone": rng.choice(CORNERS),
            }
        )
    # the opponent: numbers only; a part of its goals comes from our right side's wing (RA)
    opp_numbers = [3, 5, 8, 10, 14, 17, 20, 23, 33]
    for k in range(opp_goals):
        pos = "RA" if k < opp_from_right_wing else pick_weighted(rng, opp_weights)
        x, y = rng.choice(SPOTS[pos])
        events.append(
            {
                "type": "shot",
                "side": "opponent",
                "outcome": "goal",
                "number": rng.choice(opp_numbers),
                "x": round(x + rng.uniform(-0.4, 0.4), 1),
                "y": round(y + rng.uniform(-0.4, 0.4), 1),
                "attributes": {"goalkeeper_id": keeper},
                # the low corner on the keeper's left gets hit most
                "goal_zone": pick_weighted(
                    rng,
                    {
                        "BL": 0.34,
                        "BR": 0.18,
                        "ML": 0.14,
                        "TL": 0.1,
                        "TR": 0.1,
                        "MC": 0.06,
                        "BC": 0.08,
                    },
                ),
            }
        )
    for _ in range(keeper_saves):
        pos = pick_weighted(rng, {**opp_weights, "RA": 0.08})
        x, y = rng.choice(SPOTS[pos])
        events.append(
            {
                "type": "shot",
                "side": "opponent",
                "outcome": "save",
                "number": rng.choice(opp_numbers),
                "x": round(x, 1),
                "y": round(y, 1),
                "goal_zone": rng.choice(CORNERS),
                "attributes": {"goalkeeper_id": keeper},
            }
        )
    for _ in range(turnovers):
        pos = rng.choice(["RL", "RM", "RR", "KM"])
        events.append(
            {
                "type": "turnover",
                "side": "own",
                "turnover_type": rng.choice(
                    ["bad_pass", "bad_pass", "catch_error", "steps", "offensive_foul"]
                ),
                "player_id": rng.choice(players[pos]),
            }
        )
    # the opponent loses the ball too, and some of our goals come from fast breaks
    for _ in range(rng.randint(9, 14)):
        events.append(
            {
                "type": "turnover",
                "side": "opponent",
                "turnover_type": rng.choice(["bad_pass", "catch_error", "steps"]),
                "number": rng.choice(opp_numbers),
            }
        )
    fast = [
        e
        for e in events
        if e["side"] == "own" and e.get("outcome") == "goal" and e.get("shot_type") is None
    ]
    for e in fast[: rng.randint(3, 5)]:
        e["shot_type"] = "fast_break"
        e["x"], e["y"] = round(rng.uniform(33, 36), 1), round(rng.uniform(7, 13), 1)
    for _ in range(rng.randint(2, 4)):
        events.append(
            {
                "type": "suspension_2min",
                "side": rng.choice(["own", "opponent"]),
                "number": rng.choice(opp_numbers),
            }
        )
    rng.shuffle(events)
    # match time over two halves of 30 minutes; video time over the synthetic clip
    n = len(events)
    for i, e in enumerate(events):
        clock = round(60 + i * (3480 / n) + rng.uniform(0, 20), 1)
        e["period"] = 1 if clock < 1800 else 2
        # match clock from the throw-off, 0 to 3600 s over both halves
        e["clock_s"] = clock
        e["t_ms"] = int(1500 + i * ((VIDEO_SECONDS - 3) * 1000 / n))
        if e["type"] == "suspension_2min" and e["side"] == "own":
            e.pop("number", None)
            e["player_id"] = rng.choice(players["RL"] + players["KM"])
    return events


def paper_report(
    rng: random.Random, when: datetime, opponent: str, home: bool, own: int, opp: int
) -> dict[str, Any]:
    field = [s for s in SQUAD if s[3] != "TW"]
    goals = [0] * len(field)
    for _ in range(own):
        goals[rng.randrange(len(field))] += 1
    players = [
        {
            "number": s[0],
            "name": f"{s[1]} {s[2]}",
            "goals": g,
            "misses": rng.randint(0, 3),
            **({"suspensions": 1} if rng.random() < 0.2 else {}),
            **({"technical_faults": {"bad_pass": rng.randint(1, 2)}} if rng.random() < 0.6 else {}),
        }
        for s, g in zip(field, goals, strict=True)
        if g or rng.random() < 0.5
    ]
    return {
        "schema": "handball-paper-report/1",
        "date": when.date().isoformat(),
        "kickoff": "19:30",
        "opponent": opponent,
        "home": home,
        "competition": "2. Liga Herren",
        "score": {"own": own, "opponent": opp},
        "halftime": {"own": own // 2 + rng.randint(-1, 1), "opponent": opp // 2},
        "players": players,
        "goalkeepers": [{"number": 1, "name": "Andrin Gerber", "saves": rng.randint(9, 14)}],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--web", default="http://localhost:3000")
    ap.add_argument("--videos", type=int, default=3, help="matches with video (at most 3)")
    args = ap.parse_args()
    rng = random.Random(2026)
    c = Client(args.web)
    if (
        c.http.post("/v1/auth/login", json={"email": EMAIL, "password": PASSWORD}).status_code
        == 200
    ):
        print(f"demo account exists already: {EMAIL}")
        return
    c.post(
        "/v1/auth/register",
        json={"email": EMAIL, "name": "Sandra Lüthi", "password": PASSWORD, "accept_terms": True},
    )
    org = c.post(
        "/v1/orgs",
        json={
            "name": CLUB,
            "primary_color": "#0b3d91",
            "secondary_color": "#ffffff",
            "kit_pattern": "hoops",
        },
    ).json()["id"]
    o = f"/v1/orgs/{org}"

    # Herren 1 with its confirmed squad, U17 with a small one
    herren = c.post(
        f"{o}/teams",
        json={"name": "Herren 1", "gender": "men", "is_youth": False, "league": "2. Liga Herren"},
    ).json()
    season = herren["current_season"]["id"]
    roster_url = f"{o}/teams/{herren['id']}/seasons/{season}/roster"
    by_position: dict[str, list[str]] = {}
    for number, first, last, pos, hand, born in SQUAD:
        entry = c.post(
            roster_url,
            json={
                "first_name": first,
                "last_name": last,
                "jersey_number": number,
                "main_position": pos,
                "shooting_hand": hand,
                "birth_year": born,
            },
        ).json()
        by_position.setdefault(pos, []).append(entry["player_id"])
    u17 = c.post(
        f"{o}/teams",
        json={
            "name": "U17 Juniorinnen",
            "gender": "women",
            "is_youth": True,
            "league": "U17 Elite",
        },
    ).json()
    u17_roster = f"{o}/teams/{u17['id']}/seasons/{u17['current_season']['id']}/roster"
    for number, first, last, pos in YOUTH:
        c.post(
            u17_roster,
            json={
                "first_name": first,
                "last_name": last,
                "jersey_number": number,
                "main_position": pos,
                "birth_year": 2010,
            },
        )

    now = datetime.now(UTC).replace(hour=18, minute=30, second=0, microsecond=0)
    base = f"{o}/teams/{herren['id']}/matches"

    # two older matches with a match report only
    for days, opponent, home, own, opp in (
        (40, "SG Horgen-Oberrieden", True, 27, 24),
        (33, "HC Meilen-Herrliberg", False, 23, 25),
    ):
        report = paper_report(rng, now - timedelta(days=days), opponent, home, own, opp)
        c.post(
            f"{o}/teams/{herren['id']}/paper-reports",
            files={"file": ("spielbericht.json", json.dumps(report), "application/json")},
        )

    # three matches with video and events; the right wing stays open, 7 m are missed
    analysed = [
        dict(
            days=19,
            opponent="TV Au-Wädenswil",
            home=True,
            kit="#c8102e",
            own=26,
            opp=23,
            misses=19,
            saves=15,
            seven=(5, 2),
            wing=10,
            turnovers=10,
        ),
        dict(
            days=12,
            opponent="BSV Stäfa-Uerikon",
            home=False,
            kit="#1b7a3e",
            own=24,
            opp=27,
            misses=22,
            saves=13,
            seven=(4, 1),
            wing=11,
            turnovers=12,
        ),
        dict(
            days=5,
            opponent="TSV Thalwil-Gattikon",
            home=True,
            kit="#ffd200",
            own=29,
            opp=25,
            misses=17,
            saves=16,
            seven=(6, 3),
            wing=9,
            turnovers=8,
        ),
    ][: max(0, min(3, args.videos))]
    matches = []
    for spec in analysed:
        m = c.post(
            base,
            json={
                "opponent_name": spec["opponent"],
                "kickoff_at": (now - timedelta(days=spec["days"])).isoformat(),
                "is_home": spec["home"],
                "competition": "2. Liga Herren",
                "venue": "Sporthalle Rotweg, Horgen" if spec["home"] else None,
                "kit_own": "#0b3d91",
                "kit_own_gk": "#f28c00",
                "opponent_kit": spec["kit"],
                "kit_opponent": spec["kit"],
                "kit_opponent_gk": "#111111",
                "is_demo": True,
            },
        ).json()
        events = match_events(
            rng,
            players=by_position,
            own_goals=spec["own"],
            opp_goals=spec["opp"],
            own_misses=spec["misses"],
            keeper_saves=spec["saves"],
            seven_m=spec["seven"],
            opp_from_right_wing=spec["wing"],
            turnovers=spec["turnovers"],
            keeper=by_position["TW"][0],
        )
        for e in events:
            c.post(f"{o}/matches/{m['id']}/events", json=e)
        c.patch(
            f"{o}/matches/{m['id']}",
            json={
                "score_own": spec["own"],
                "score_opponent": spec["opp"],
                # the half-time score as the events have it
                "halftime_own": sum(
                    e["side"] == "own" and e.get("outcome") == "goal" and e["period"] == 1
                    for e in events
                ),
                "halftime_opponent": sum(
                    e["side"] == "opponent" and e.get("outcome") == "goal" and e["period"] == 1
                    for e in events
                ),
            },
        )
        matches.append(m["id"])
        print(f"match against {spec['opponent']}: {len(events)} events")

    # the next opponent, without a colour yet (nobody said it: it stays unknown)
    c.post(
        base,
        json={
            "opponent_name": "TV Au-Wädenswil",
            "kickoff_at": (now + timedelta(days=4)).isoformat(),
            "is_home": False,
            "competition": "2. Liga Herren",
        },
    )

    with tempfile.TemporaryDirectory() as tmp:
        for k, mid in enumerate(matches):
            video = Path(tmp) / f"spiel{k}.mp4"
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "handball_vision.synthetic",
                    str(video),
                    "--seconds",
                    str(VIDEO_SECONDS),
                    "--seed",
                    str(11 + k),
                    "--demo",
                ],
                check=True,
            )
            upload(c, org, mid, video)
            print(f"uploaded synthetic video for match {mid}")

    if matches:
        coll = c.post(
            f"{o}/teams/{herren['id']}/collections/from-match",
            json={"match_id": matches[-1], "title": "Rückzug und rechter Flügel"},
        ).json()
        c.patch(f"{o}/collections/{coll['id']}", json={"draft": False})
        print(f"collection with {len(coll['items'])} scenes")
    print(f"Demo ready. Sign in at {args.web}/login with {EMAIL} / {PASSWORD}")


if __name__ == "__main__":
    main()

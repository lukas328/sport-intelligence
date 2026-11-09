"""Demo data (BRIEF 15): `make seed` against the running stack (docker compose up).

Creates a demo club with two teams, rosters, five matches and two synthetic match videos that run
through the real pipeline (upload, ingest, analysis). Everything is marked as demo; the videos are
rendered by packages/vision (synthetic, not real footage).

    uv run python scripts/seed.py [--web http://localhost:3000]
"""

from __future__ import annotations

import argparse
import math
import random
import subprocess
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

EMAIL = "demo@handball-demo.ch"
PASSWORD = "demo-handball-2026"  # noqa: S105 (local demo account)
FIRST = [
    "Lena",
    "Mia",
    "Noah",
    "Luca",
    "Elias",
    "Tim",
    "Nico",
    "Jan",
    "Levin",
    "Finn",
    "Leon",
    "Ben",
    "Jonas",
    "Rafael",
    "Sara",
    "Lara",
    "Nina",
    "Alina",
    "Jana",
    "Elena",
    "Julia",
    "Laura",
]
LAST = [
    "Meier",
    "Keller",
    "Huber",
    "Brunner",
    "Frei",
    "Weber",
    "Schmid",
    "Gerber",
    "Baumann",
    "Zürcher",
    "Graf",
    "Steiner",
    "Moser",
    "Kunz",
    "Roth",
    "Bühler",
]
POS = ["TW", "LA", "RL", "RM", "RR", "RA", "KM", "TW", "RL", "RM", "RR", "LA", "RA", "KM"]


class Client:
    def __init__(self, web: str) -> None:
        self.http = httpx.Client(base_url=web, timeout=60, headers={"origin": web})

    def _h(self) -> dict[str, str]:
        csrf = self.http.cookies.get("hb_csrf")
        return {"x-csrf-token": csrf} if csrf else {}

    def get(self, url: str) -> httpx.Response:
        return self.http.get(url)

    def post(self, url: str, **kw: object) -> httpx.Response:
        r = self.http.post(url, headers=self._h(), **kw)  # type: ignore[arg-type]
        if r.status_code >= 400:
            sys.exit(f"POST {url} -> {r.status_code} {r.text[:300]}")
        return r

    def patch(self, url: str, **kw: object) -> httpx.Response:
        return self.http.patch(url, headers=self._h(), **kw)  # type: ignore[arg-type]


def upload(c: Client, org: str, match: str, path: Path) -> None:
    size = path.stat().st_size
    up = c.post(
        f"/v1/orgs/{org}/matches/{match}/videos", json={"filename": "demo.mp4", "size_bytes": size}
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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--web", default="http://localhost:3000")
    ap.add_argument("--videos", type=int, default=2)
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
        json={"email": EMAIL, "name": "Demo Trainerin", "password": PASSWORD, "accept_terms": True},
    )
    org = c.post(
        "/v1/orgs", json={"name": "HC Demo Zürichsee (Demo)", "primary_color": "#c8102e"}
    ).json()["id"]
    teams = []
    for name, gender, youth in (("Herren 1", "men", False), ("U17 Juniorinnen", "women", True)):
        t = c.post(
            f"/v1/orgs/{org}/teams",
            json={"name": name, "gender": gender, "is_youth": youth, "league": "Demo-Liga"},
        ).json()
        teams.append(t)
        roster = f"/v1/orgs/{org}/teams/{t['id']}/seasons/{t['current_season']['id']}/roster"
        names = rng.sample(FIRST[:14] if gender == "men" else FIRST[8:], 10) + rng.sample(FIRST, 4)
        for i, first in enumerate(names):
            c.post(
                roster,
                json={
                    "first_name": first,
                    "last_name": rng.choice(LAST),
                    "jersey_number": i + 2 if i else 1,
                    "main_position": POS[i],
                    "shooting_hand": "left" if i % 5 == 4 else "right",
                    "birth_year": 2001 + i % 6 if not youth else 2009 + i % 2,
                },
            )
    home = teams[0]["id"]
    now = datetime.now(UTC)
    opponents = [
        "TV Demo-Wädenswil",
        "SG Demo-Horgen",
        "HC Demo-Meilen",
        "BSV Demo-Stäfa",
        "TSV Demo-Thalwil",
    ]
    matches = []
    for k, opp in enumerate(opponents):
        own = 24 + int(6 * math.sin(k * 1.7))
        other = 22 + int(5 * math.cos(k * 2.3))
        m = c.post(
            f"/v1/orgs/{org}/teams/{home}/matches",
            json={
                "opponent_name": opp,
                "kickoff_at": (now - timedelta(days=7 * (len(opponents) - k))).isoformat(),
                "is_home": k % 2 == 0,
                "competition": "Demo-Liga",
                "kit_own": "#2828c8",
                "kit_own_gk": "#e6c828",
                "kit_opponent": "#ebe6e6",
                "kit_opponent_gk": "#3caa3c",
                "is_demo": True,
            },
        ).json()
        c.patch(
            f"/v1/orgs/{org}/matches/{m['id']}",
            json={
                "score_own": own,
                "score_opponent": other,
                "halftime_own": own // 2,
                "halftime_opponent": other // 2,
            },
        )
        matches.append(m["id"])
    with tempfile.TemporaryDirectory() as tmp:
        for k, mid in enumerate(matches[-args.videos :]):
            video = Path(tmp) / f"demo{k}.mp4"
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "handball_vision.synthetic",
                    str(video),
                    "--seconds",
                    "60",
                    "--seed",
                    str(11 + k),
                    "--demo",
                ],
                check=True,
            )
            upload(c, org, mid, video)
            print(f"uploaded synthetic video for match {mid}")
    print(f"Demo ready. Sign in at {args.web}/login with {EMAIL} / {PASSWORD}")


if __name__ == "__main__":
    main()

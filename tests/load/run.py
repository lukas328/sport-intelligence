"""Load test for the read paths coaches and players hit most (M9).

Seeds one club with a season of tagged matches, then runs N concurrent users for D seconds
against match page, events list, stats, insights, season stats, notifications, playlists and plays.
Prints latency percentiles per endpoint and the error rate; exits 1 when the p95 budget is broken.

    uv run python tests/load/run.py --base http://localhost:8000 --users 50 --seconds 60
"""

from __future__ import annotations

import argparse
import asyncio
import random
import statistics
import time
import uuid
from collections import defaultdict

import httpx

ORIGIN = "http://localhost:3000"


async def session(base: str) -> httpx.AsyncClient:
    c = httpx.AsyncClient(base_url=base, timeout=30, headers={"origin": ORIGIN})
    return c


def csrf(c: httpx.AsyncClient) -> dict[str, str]:
    return {"x-csrf-token": c.cookies.get("hb_csrf", "")}


async def seed(base: str, matches: int) -> tuple[str, str, str, list[str], list[tuple[str, str]]]:
    c = await session(base)
    email = f"load-{uuid.uuid4().hex[:8]}@hc-load.ch"
    r = await c.post(
        "/v1/auth/register",
        json={
            "email": email,
            "password": "correct-horse-1",
            "name": "Load Coach",
            "accept_terms": True,
        },
    )
    r.raise_for_status()
    r = await c.post("/v1/orgs", json={"name": "HC Load"}, headers=csrf(c))
    r.raise_for_status()
    org = r.json()["id"]
    team = (
        await c.post(
            f"/v1/orgs/{org}/teams", json={"name": "Herren", "gender": "men"}, headers=csrf(c)
        )
    ).json()
    team_id, season = team["id"], team["current_season"]["id"]
    ids = []
    rnd = random.Random(1)
    for i in range(matches):
        m = (
            await c.post(
                f"/v1/orgs/{org}/teams/{team_id}/matches",
                json={
                    "opponent_name": f"Gegner {i % 5}",
                    "kickoff_at": f"2026-09-{i + 1:02d}T18:00:00+02:00",
                },
                headers=csrf(c),
            )
        ).json()
        ids.append(m["id"])
        for k in range(60):
            side = "own" if k % 2 else "opponent"
            body = {
                "type": "shot",
                "side": side,
                "outcome": rnd.choice(["goal", "goal", "save", "miss"]),
                "clock_s": k * 55 + 5,
                "x": rnd.uniform(28, 38),
                "y": rnd.uniform(2, 18),
                "number": 7 + k % 6,
            }
            await c.post(f"/v1/orgs/{org}/matches/{m['id']}/events", json=body, headers=csrf(c))
    cookies = [(name, value) for name, value in c.cookies.items()]
    await c.aclose()
    return org, team_id, season, ids, cookies


async def user(
    base: str,
    cookies: list[tuple[str, str]],
    paths: list[tuple[str, str]],
    until: float,
    lat: dict[str, list[float]],
    errors: dict[str, int],
) -> None:
    async with httpx.AsyncClient(base_url=base, timeout=30) as c:
        for k, v in cookies:
            c.cookies.set(k, v)
        while time.perf_counter() < until:
            name, path = random.choice(paths)
            t0 = time.perf_counter()
            try:
                r = await c.get(path)
                ok = r.status_code < 400
            except httpx.HTTPError:
                ok = False
            lat[name].append((time.perf_counter() - t0) * 1000)
            if not ok:
                errors[name] += 1


async def open_loop(
    base: str,
    cookies: list[tuple[str, str]],
    paths: list[tuple[str, str]],
    until: float,
    rate: float,
    lat: dict[str, list[float]],
    errors: dict[str, int],
) -> None:
    """Fixed arrival rate (Poisson), independent of response times: shows queueing honestly."""
    limits = httpx.Limits(max_connections=200)
    async with httpx.AsyncClient(base_url=base, timeout=30, limits=limits) as c:
        for k, v in cookies:
            c.cookies.set(k, v)

        async def one(name: str, path: str) -> None:
            t0 = time.perf_counter()
            try:
                ok = (await c.get(path)).status_code < 400
            except httpx.HTTPError:
                ok = False
            lat[name].append((time.perf_counter() - t0) * 1000)
            if not ok:
                errors[name] += 1

        tasks = []
        while time.perf_counter() < until:
            tasks.append(asyncio.create_task(one(*random.choice(paths))))
            await asyncio.sleep(random.expovariate(rate))
        await asyncio.gather(*tasks)


def pct(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    return s[min(len(s) - 1, round(p / 100 * (len(s) - 1)))]


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8000")
    ap.add_argument("--users", type=int, default=50)
    ap.add_argument("--seconds", type=int, default=60)
    ap.add_argument("--matches", type=int, default=10)
    ap.add_argument("--p95-budget-ms", type=float, default=300)
    ap.add_argument(
        "--rate", type=float, default=0, help="open loop: requests per second (0 = closed loop)"
    )
    a = ap.parse_args()
    org, team, season, matches, cookies = await seed(a.base, a.matches)
    m = matches[-1]
    paths = [
        ("match", f"/v1/orgs/{org}/matches/{m}"),
        ("events", f"/v1/orgs/{org}/matches/{m}/events"),
        ("stats", f"/v1/orgs/{org}/matches/{m}/stats"),
        ("insights", f"/v1/orgs/{org}/matches/{m}/insights"),
        ("season", f"/v1/orgs/{org}/teams/{team}/seasons/{season}/stats"),
        ("notifications", f"/v1/orgs/{org}/me/notifications"),
        ("playlists", f"/v1/orgs/{org}/teams/{team}/playlists"),
        ("plays", f"/v1/orgs/{org}/teams/{team}/plays"),
        ("matches", f"/v1/orgs/{org}/teams/{team}/matches"),
    ]
    lat: dict[str, list[float]] = defaultdict(list)
    errors: dict[str, int] = defaultdict(int)
    until = time.perf_counter() + a.seconds
    started = time.perf_counter()
    if a.rate:
        await open_loop(a.base, cookies, paths, until, a.rate, lat, errors)
    else:
        await asyncio.gather(
            *(user(a.base, cookies, paths, until, lat, errors) for _ in range(a.users))
        )
    elapsed = time.perf_counter() - started
    total = sum(len(v) for v in lat.values())
    print(f"users={a.users} seconds={a.seconds} requests={total} rps={total / elapsed:.0f}")
    print(f"{'endpoint':14} {'n':>6} {'p50':>7} {'p95':>7} {'p99':>7} {'err':>5}")
    worst = 0.0
    for name, _ in paths:
        v = lat[name]
        p95 = pct(v, 95)
        worst = max(worst, p95)
        print(
            f"{name:14} {len(v):6} {statistics.median(v):7.0f} {p95:7.0f} "
            f"{pct(v, 99):7.0f} {errors[name]:5}"
        )
    err_rate = sum(errors.values()) / max(1, total)
    print(f"error rate {err_rate:.2%}, worst p95 {worst:.0f} ms (budget {a.p95_budget_ms:.0f} ms)")
    return 0 if worst <= a.p95_budget_ms and err_rate < 0.01 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

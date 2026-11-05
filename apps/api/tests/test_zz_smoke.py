"""Temporary exploratory smoke test (removed before commit)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from handball_api.core.jobs import MemoryJobQueue

from .conftest import Api, setup_club
from .test_identity_sync import _finish
from .test_matches import new_match, upload
from .test_official_report import CH_URL, recorded  # noqa: F401

pytestmark = pytest.mark.usefixtures("clean_db")


async def _ingest(api: Api, job_id: str, prefix: str, duration: float) -> None:
    token = {"x-internal-token": api.app.state.settings.internal_token.get_secret_value()}
    r = await api.http.post(
        f"/internal/jobs/{job_id}",
        headers=token,
        json={
            "status": "succeeded",
            "progress": 1,
            "result": {
                "proxy_key": prefix + "proxy.mp4",
                "hls_prefix": prefix + "hls/",
                "duration_s": duration,
            },
        },
    )
    assert r.status_code == 200, r.text


async def hit_all(api: Api, ids: dict[str, Any], mid: str, vid: str) -> list[str]:
    org = ids["org"]
    base = f"/v1/orgs/{org}/matches/{mid}"
    bad = []
    gets = [
        base,
        f"{base}/events",
        f"{base}/stats",
        f"{base}/possessions",
        f"{base}/physical",
        f"{base}/insights",
        f"{base}/boundaries",
        f"{base}/parts",
        f"{base}/goal-candidates",
        f"{base}/official-report/comparison",
        f"{base}/feed",
        f"{base}/highlights",
        f"{base}/clips",
        f"{base}/marks",
        f"{base}/scouting",
        f"{base}/report.pdf",
        f"{base}/export/sportscode",
        f"{base}/export/events",
        f"{base}/exports/shots",
        f"{base}/tag-links",
        f"/v1/orgs/{org}/videos/{vid}/analysis",
        f"/v1/orgs/{org}/videos/{vid}/panorama",
        f"/v1/orgs/{org}/videos/{vid}/tracks/0",
        f"/v1/orgs/{org}/teams/{ids['team']}/search",
        f"/v1/orgs/{org}/teams/{ids['team']}/seasons/{ids['season']}/stats",
    ]
    for u in gets:
        try:
            r = await api.get(u)
        except Exception as exc:
            bad.append(f"GET {u} EXC {type(exc).__name__}: {str(exc)[:1500]}")
            continue
        if r.status_code >= 500:
            bad.append(f"GET {u} {r.status_code}")
    posts: list[tuple[str, dict[str, Any]]] = [
        (f"{base}/feed/generate", {}),
        (f"{base}/highlights", {"format": "landscape"}),
        
        (f"{base}/scouting", {}),
    ]
    for u, body in posts:
        try:
            r = await api.post(u, json=body)
        except Exception as exc:
            bad.append(f"POST {u} EXC {type(exc).__name__}: {str(exc)[:1500]}")
            continue
        if r.status_code >= 500:
            bad.append(f"POST {u} {r.status_code} {r.text[:200]}")
    ins = (await api.get(f"{base}/insights")).json()
    for item in ins.get("insights", []) if isinstance(ins, dict) else []:
        try:
            r = await api.post(
                f"{base}/focus",
                json={"insight_key": item["key"], "params": item.get("params") or {}},
            )
        except Exception as exc:
            bad.append(f"POST focus {item['key']} EXC {str(exc)[:200]}")
            continue
        if r.status_code >= 500:
            bad.append(f"POST focus {item['key']} {r.status_code}")
    return bad


async def test_mid_half_clip_with_official_report(
    make_api: Callable[[], Api],
    recorded: Any,  # noqa: F811
) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    roster = f"/v1/orgs/{org}/teams/{ids['team']}/seasons/{ids['season']}/roster"
    for n in (7, 33, 1, 6, 9):
        await api.post(roster, json={"first_name": f"P{n}", "last_name": "X", "jersey_number": n})
    m = await new_match(api, ids, opponent_name="HC Arbon")
    r = await api.post(f"/v1/orgs/{org}/matches/{m['id']}/official-report", json={"url": CH_URL})
    assert r.status_code == 200
    up = await upload(api, ids, m["id"], b"v" * 100)
    jobs: MemoryJobQueue = api.app.state.jobs
    await _ingest(api, jobs.jobs[-1][2], jobs.jobs[-1][3]["prefix"], 300.0)
    overlay = {
        "goals": [{"t_ms": 35_000, "side": "left", "score": [5, 6]}],
        "clock": [{"start_ms": 0, "end_ms": 300_000, "start_clock_s": 1200, "reads": 50}],
    }
    await _finish(api, jobs.jobs[-1][2], {"tracks": [], "detector": "model", "scoreboard": overlay})
    bad = await hit_all(api, ids, m["id"], up["id"])
    print("\nBAD:\n" + "\n".join(bad))
    assert not bad


async def test_zero_results(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    m = await new_match(api, ids)
    up = await upload(api, ids, m["id"], b"v" * 100)
    jobs: MemoryJobQueue = api.app.state.jobs
    await _ingest(api, jobs.jobs[-1][2], jobs.jobs[-1][3]["prefix"], 7200.0)
    await _finish(
        api,
        jobs.jobs[-1][2],
        {"needs_calibration": True, "calibration_error": "flat view", "panorama": {"width": 1920, "height": 1080}},
    )
    bad = await hit_all(api, ids, m["id"], up["id"])
    print("\nBAD:\n" + "\n".join(bad))
    assert not bad


async def test_no_video(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    m = await new_match(api, ids)
    up = await upload(api, ids, m["id"], b"v" * 100)
    bad = await hit_all(api, ids, m["id"], up["id"])
    print("\nBAD:\n" + "\n".join(bad))
    assert not bad


async def test_inspect(make_api: Callable[[], Api], recorded: Any) -> None:  # noqa: F811
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    m = await new_match(api, ids, opponent_name="HC Arbon")
    await api.post(f"/v1/orgs/{org}/matches/{m['id']}/official-report", json={"url": CH_URL})
    up = await upload(api, ids, m["id"], b"v" * 100)
    jobs: MemoryJobQueue = api.app.state.jobs
    await _ingest(api, jobs.jobs[-1][2], jobs.jobs[-1][3]["prefix"], 300.0)
    overlay = {
        "goals": [{"t_ms": 35_000, "side": "left", "score": [5, 6]}],
        "clock": [{"start_ms": 0, "end_ms": 300_000, "start_clock_s": 1200, "reads": 50}],
    }
    await _finish(api, jobs.jobs[-1][2], {"tracks": [], "detector": "model", "scoreboard": overlay})
    base = f"/v1/orgs/{org}/matches/{m['id']}"
    x = (await api.get(f"{base}/export/sportscode")).text
    import re as _re
    print("SPORTSCODE neg:", len(_re.findall(r"<end>-", x)), "total", x.count("<instance>"))
    s = (await api.get(f"/v1/orgs/{org}/teams/{ids['team']}/search")).json()
    print("SEARCH bad windows:", [(h["start_ms"], h["end_ms"]) for h in s["hits"] if h["end_ms"] is not None and h["end_ms"] <= h["start_ms"]][:5], "of", len(s["hits"]))
    shots = (await api.get(f"{base}/exports/shots")).json()
    print("SHOTS keys", list(shots)[:10])
    print("VID", up["id"])


async def test_pres(make_api: Callable[[], Api]) -> None:
    coach = make_api()
    ids = await setup_club(coach)
    org, team = ids["org"], ids["team"]
    o = f"/v1/orgs/{org}"
    m = await new_match(coach, ids)  # no video at all
    clip = (
        await coach.post(f"{o}/clips", json={"match_id": m["id"], "start_ms": 1000, "end_ms": 8000})
    ).json()
    pres = (
        await coach.post(f"{o}/teams/{team}/presentations", json={"title": "T", "match_id": m["id"]})
    ).json()
    for body in (
        {"type": "clip", "clip_id": clip["id"], "content": {}},
        {"type": "clip", "content": {"video_id": "nope", "in_ms": 0, "out_ms": 5}},
    ):
        try:
            r = await coach.post(f"{o}/presentations/{pres['id']}/slides", json=body)
            print("PRES", r.status_code, r.text[:200])
        except Exception as exc:
            print("PRES EXC", type(exc).__name__, str(exc)[:200])

"""Automatic events from the analysis (addendum 01, A3)."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from handball_api.core.jobs import MemoryJobQueue

from .conftest import Api, setup_club
from .test_identity_sync import _finish, _ingest, _tracks
from .test_matches import new_match, upload

pytestmark = pytest.mark.usefixtures("clean_db")

AUTO = {
    "events": [
        {"t_ms": 8000, "type": "throw_off", "team": "home", "confidence": 0.9},
        {
            "t_ms": 61_600,
            "type": "goal",
            "team": "home",
            "confidence": 0.77,
            "inferred_from": "throw_off",
        },
        {"t_ms": 61_600, "type": "possession_change", "team": "away", "confidence": 0.9},
        {"t_ms": 68_000, "type": "throw_off", "team": "away", "confidence": 0.9},
        {"t_ms": 81_600, "type": "goal", "team": "away", "confidence": 0.75},
        {"t_ms": 88_000, "type": "throw_off", "team": "home", "confidence": 0.88},
        {"t_ms": 95_000, "type": "goal", "team": "away", "confidence": 0.3},
        {"t_ms": 100_000, "type": "side_change", "team": None, "confidence": 0.8},
        {"t_ms": 108_000, "type": "throw_off", "team": "away", "confidence": 0.9},
    ],
    "possessions": [
        {"team": "home", "start_ms": 9000, "end_ms": 21_600, "confidence": 0.9, "outcome": "lost"},
        {
            "team": "away",
            "start_ms": 23_000,
            "end_ms": 41_600,
            "confidence": 0.9,
            "outcome": "lost",
        },
        {
            "team": "home",
            "start_ms": 43_200,
            "end_ms": 61_600,
            "confidence": 0.9,
            "outcome": "goal",
        },
    ],
    "sides": [
        {"from_ms": 2800, "home_defends": "left"},
        {"from_ms": 100_000, "home_defends": "right"},
    ],
    "missing": [],
}


async def test_auto_events_from_analysis(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    m = await new_match(api, ids)
    ev_url = f"/v1/orgs/{org}/matches/{m['id']}/events"
    # a goal tagged by hand close to the automatic one wins
    await api.post(
        ev_url, json={"type": "shot", "side": "opponent", "outcome": "goal", "t_ms": 80_000}
    )
    await upload(api, ids, m["id"], b"v" * 100)
    jobs: MemoryJobQueue = api.app.state.jobs
    await _ingest(api, jobs.jobs[-1][2], jobs.jobs[-1][3]["prefix"])
    await _finish(
        api, jobs.jobs[-1][2], {"tracks": _tracks(), "detector": "heuristic", "events": AUTO}
    )

    match = (await api.get(f"/v1/orgs/{org}/matches/{m['id']}")).json()
    assert match["kickoff_ms"] == {"1": 8000, "2": 108_000}  # clock from the opening throw-offs
    events = (await api.get(ev_url)).json()
    auto = [e for e in events if e["source"] == "heuristic"]
    assert sorted((e["type"], e["side"], e["t_ms"]) for e in auto) == [
        ("shot", "own", 61_600),
        ("throw_off", "opponent", 68_000),
        ("throw_off", "opponent", 108_000),
        ("throw_off", "own", 8000),
        ("throw_off", "own", 88_000),
    ]
    goal = next(e for e in auto if e["type"] == "shot")
    assert goal["confidence"] == 0.77 and goal["clock_s"] == 53.6 and goal["outcome"] == "goal"
    stats = (await api.get(f"/v1/orgs/{org}/matches/{m['id']}/stats")).json()
    assert stats["own"]["goals"] == 1 and stats["opponent"]["goals"] == 1
    assert stats["possessions_source"] == "tracking"
    a = (await api.get(f"/v1/orgs/{org}/videos/{jobs.jobs[-1][3]['asset_id']}/analysis")).json()
    assert a["status"] == "ready"

    # a re-run of the analysis replaces the automatic rows, manual ones stay
    await _finish(
        api, jobs.jobs[-1][2], {"tracks": _tracks(), "detector": "heuristic", "events": AUTO}
    )
    again = (await api.get(ev_url)).json()
    assert len([e for e in again if e["source"] == "heuristic"]) == 5
    assert len([e for e in again if e["source"] != "heuristic"]) == 1

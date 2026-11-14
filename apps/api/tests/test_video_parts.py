"""One match over several files (Q-VIDEO-PARTS): two halves, a recording the phone split.

The parts lie one after the other on the match timeline; each part is analysed on its own and its
results are placed at the part's start. A part added later, deleted or swapped moves everything of
the match with it, and nothing the coach confirmed is lost.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from handball_api.core.jobs import MemoryJobQueue
from handball_api.core.storage import MemoryStorage

from .conftest import Api, setup_club
from .test_auto_events import AUTO
from .test_goal_candidates import FOUND, _cand
from .test_identity_sync import _finish, _tracks
from .test_matches import new_match, upload

pytestmark = pytest.mark.usefixtures("clean_db")

ANALYSIS = "handball_gpu_worker.analysis.run_analysis"
HALF = 1_800_000  # 30 minutes
# the first half alone: the automatic events of the test clip before its side change
FIRST = {
    **AUTO,
    "events": [e for e in AUTO["events"] if int(e["t_ms"]) < 100_000],  # type: ignore[call-overload]
    "sides": [{"from_ms": 2800, "home_defends": "left"}],
}


def _token(api: Api) -> dict[str, str]:
    return {"x-internal-token": api.app.state.settings.internal_token.get_secret_value()}


def _jobs(api: Api) -> MemoryJobQueue:
    jobs: MemoryJobQueue = api.app.state.jobs
    return jobs


def _job_of(api: Api, video_id: str, func: str) -> tuple[str, dict[str, Any]]:
    job = [j for j in _jobs(api).jobs if j[1] == func and j[3].get("asset_id") == video_id][-1]
    return job[2], job[3]


async def _ingest(
    api: Api,
    video_id: str,
    duration_ms: int,
    recorded: str | None = None,
    checksum: str | None = None,
) -> None:
    job = [
        j
        for j in _jobs(api).jobs
        if j[1] == "handball_worker.ingest.run_ingest" and j[3]["asset_id"] == video_id
    ][-1]
    prefix = job[3]["prefix"]
    await _finish(
        api,
        job[2],
        {
            "proxy_key": prefix + "proxy.mp4",
            "hls_prefix": prefix + "hls/",
            "duration_s": duration_ms / 1000,
            "recorded_at": recorded,
            "checksum_sha256": checksum or video_id.replace("-", "")[:32],
        },
    )


async def _analyse(api: Api, video_id: str, again: bool = False, **extra: Any) -> dict[str, Any]:
    if again:  # a new run of this part's analysis («Erneut versuchen»)
        org = _job_of(api, video_id, ANALYSIS)[1]["organization_id"]
        assert (await api.post(f"/v1/orgs/{org}/videos/{video_id}/analysis")).status_code == 202
    job, payload = _job_of(api, video_id, ANALYSIS)
    await _finish(api, job, {"tracks": _tracks(), "detector": "model", **extra})
    return payload


async def _two_halves(api: Api, ids: dict[str, Any]) -> tuple[str, str, str]:
    """A match with both halves uploaded and analysed (the second half with its own events)."""
    m = await new_match(api, ids)
    first = await upload(api, ids, m["id"], b"a" * 100, name="halbzeit1.mp4")
    await _ingest(api, first["id"], HALF, "2026-11-07T18:00:00Z")
    await _analyse(api, first["id"], events=FIRST, goal_candidates=FOUND)
    second = await upload(api, ids, m["id"], b"b" * 100, name="halbzeit2.mp4")
    await _ingest(api, second["id"], HALF, "2026-11-07T18:45:00Z")
    return m["id"], first["id"], second["id"]


SECOND = {
    "events": [
        {"t_ms": 4000, "type": "throw_off", "team": "away", "confidence": 0.9},
        {"t_ms": 50_000, "type": "goal", "team": "away", "confidence": 0.8},
        {"t_ms": 56_000, "type": "throw_off", "team": "home", "confidence": 0.9},
    ],
    "possessions": [
        {"team": "away", "start_ms": 5000, "end_ms": 50_000, "confidence": 0.9, "outcome": "goal"}
    ],
    "sides": [{"from_ms": 0, "home_defends": "right"}],
    "missing": [],
}


async def test_both_halves_on_one_match_timeline(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    match_id, first, second = await _two_halves(api, ids)
    base = f"/v1/orgs/{org}/matches/{match_id}"
    before = {e["id"]: e["t_ms"] for e in (await api.get(f"{base}/events")).json()}

    # the second half knows the teams changed ends: home defended left at the end of the first
    payload = await _analyse(
        api, second, events=SECOND, goal_candidates={"candidates": [_cand(52_000, 1)]}
    )
    assert payload["side_hint"] == "right"
    assert "side_hint" not in _job_of(api, first, ANALYSIS)[1]

    events = (await api.get(f"{base}/events")).json()
    # the first half's events stay where they were
    assert {e["id"]: e["t_ms"] for e in events if e["id"] in before} == before
    later = sorted(
        (e["type"], e["side"], e["t_ms"]) for e in events if e["t_ms"] and e["t_ms"] >= HALF
    )
    assert later == [
        ("shot", "opponent", HALF + 50_000),
        ("throw_off", "opponent", HALF + 4000),
        ("throw_off", "own", HALF + 56_000),
    ]
    goal = next(e for e in events if e["t_ms"] == HALF + 50_000)
    # the second half's clock: its first throw-off opens it
    match = (await api.get(base)).json()
    assert match["kickoff_ms"]["2"] == HALF + 4000
    assert goal["period"] == 2 and goal["clock_s"] == 1800 + 46.0
    assert [(v["part"], v["part_start_ms"]) for v in match["videos"]] == [(1, 0), (2, HALF)]

    possessions = (await api.get(f"{base}/possessions")).json()
    assert any(p["start_ms"] == HALF + 5000 for p in possessions["phases"])
    assert any(p["start_ms"] < HALF for p in possessions["phases"])

    # Prüfen asks about moments of both halves, at match times
    cands = (await api.get(f"{base}/goal-candidates")).json()["candidates"]
    assert [c["t_ms"] for c in cands] == [63_000, 150_000, 200_000, 305_000, HALF + 52_000]
    assert cands[-1]["video_asset_id"] == second

    g = (await api.get(f"{base}/graphics")).json()
    assert [(p["video_id"], p["start_ms"], p["analysis"]) for p in g["parts"]] == [
        (first, 0, "ready"),
        (second, HALF, "ready"),
    ]
    stats = (await api.get(f"{base}/stats")).json()
    assert stats["opponent"]["goals"] >= 1 and stats["own"]["goals"] >= 1

    # the second half analysed again replaces only its own automatic rows
    await _analyse(api, second, again=True, events=SECOND)
    again = (await api.get(f"{base}/events")).json()
    assert sorted(e["t_ms"] or 0 for e in again) == sorted(e["t_ms"] or 0 for e in events)


async def test_second_half_hours_later_keeps_what_was_confirmed(
    make_api: Callable[[], Api],
) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    m = await new_match(api, ids)
    base = f"/v1/orgs/{org}/matches/{m['id']}"
    first = await upload(api, ids, m["id"], b"a" * 100, name="halbzeit1.mp4")
    await _ingest(api, first["id"], HALF)
    await _analyse(api, first["id"], events=FIRST, goal_candidates=FOUND)
    cands = (await api.get(f"{base}/goal-candidates")).json()["candidates"]
    r = await api.put(
        f"{base}/goal-candidates/{cands[0]['id']}/review",
        json={"status": "confirmed", "side": "own"},
    )
    assert r.status_code == 200, r.text
    confirmed = r.json()["event_id"]
    tagged = (
        await api.post(
            f"{base}/events",
            json={"type": "shot", "side": "opponent", "outcome": "goal", "t_ms": 400_000},
        )
    ).json()

    # the second file, hours later (no camera clock: it comes after the first)
    second = await upload(api, ids, m["id"], b"b" * 100, name="zweite.mp4")
    await _ingest(api, second["id"], HALF)
    await _analyse(api, second["id"], events=SECOND)
    events = {e["id"]: e for e in (await api.get(f"{base}/events")).json()}
    assert events[confirmed]["t_ms"] == cands[0]["goal_ms"]
    assert events[tagged["id"]]["t_ms"] == 400_000
    after = (await api.get(f"{base}/goal-candidates")).json()["candidates"]
    assert next(c for c in after if c["id"] == cands[0]["id"])["status"] == "confirmed"


async def test_an_earlier_part_added_later_moves_the_match(make_api: Callable[[], Api]) -> None:
    """The second half was uploaded first; the first half comes later and goes before it (its
    camera clock is earlier): everything of the second half moves back by the first's length."""
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    m = await new_match(api, ids)
    base = f"/v1/orgs/{org}/matches/{m['id']}"
    second = await upload(api, ids, m["id"], b"b" * 100, name="halbzeit2.mp4")
    await _ingest(api, second["id"], HALF, "2026-11-07T18:45:00Z")
    await _analyse(
        api, second["id"], events=SECOND, goal_candidates={"candidates": [_cand(52_000, 1)]}
    )
    cand = (await api.get(f"{base}/goal-candidates")).json()["candidates"][0]
    r = await api.put(
        f"{base}/goal-candidates/{cand['id']}/review",
        json={"status": "confirmed", "side": "opponent"},
    )
    event_id = r.json()["event_id"]
    clip = (
        await api.post(
            f"/v1/orgs/{org}/clips",
            json={"match_id": m["id"], "start_ms": 40_000, "end_ms": 52_000, "title": "x"},
        )
    ).json()

    first = await upload(api, ids, m["id"], b"a" * 100, name="halbzeit1.mp4")
    await _ingest(api, first["id"], HALF, "2026-11-07T18:00:00Z")
    parts = (await api.get(f"{base}/parts")).json()
    assert [(p["filename"], p["start_ms"]) for p in parts] == [
        ("halbzeit1.mp4", 0),
        ("halbzeit2.mp4", HALF),
    ]
    events = {e["id"]: e for e in (await api.get(f"{base}/events")).json()}
    assert events[event_id]["t_ms"] == cand["goal_ms"] + HALF
    moved = (await api.get(f"{base}/goal-candidates")).json()["candidates"][0]
    assert moved["t_ms"] == cand["t_ms"] + HALF and moved["status"] == "confirmed"
    clips = (await api.get(f"{base}/clips")).json()
    assert [(c["start_ms"], c["end_ms"]) for c in clips if c["id"] == clip["id"]] == [
        (40_000 + HALF, 52_000 + HALF)
    ]


async def test_swap_and_delete_parts_after_the_analysis(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    match_id, first, second = await _two_halves(api, ids)
    base = f"/v1/orgs/{org}/matches/{match_id}"
    await _analyse(api, second, events=SECOND)
    tagged = (
        await api.post(
            f"{base}/events",
            json={"type": "shot", "side": "own", "outcome": "goal", "t_ms": HALF + 600_000},
        )
    ).json()

    # «Reihenfolge stimmt nicht?»: swapped, everything moves with its file
    url = f"{base}/parts"
    swapped = (await api.put(url, json={"video_ids": [second, first]})).json()
    assert [(p["video_id"], p["start_ms"]) for p in swapped] == [(second, 0), (first, HALF)]
    events = {e["id"]: e for e in (await api.get(f"{base}/events")).json()}
    assert events[tagged["id"]]["t_ms"] == 600_000
    heuristic = sorted(e["t_ms"] for e in events.values() if e["source"] == "heuristic")
    assert heuristic[:3] == [4000, 50_000, 56_000]
    assert min(t for t in heuristic if t >= HALF) == HALF + 8000  # the first half's throw-off
    match = (await api.get(base)).json()
    assert match["kickoff_ms"] == {"1": 4000, "2": HALF + 8000}
    assert [v["id"] for v in match["videos"] if v["part"]] == [second, first]

    # swapped back, and the (now second) part deleted: its findings go, the coach's goal stays
    await api.put(url, json={"video_ids": [first, second]})
    assert (await api.delete(f"/v1/orgs/{org}/videos/{second}")).status_code == 204
    events2 = {e["id"]: e for e in (await api.get(f"{base}/events")).json()}
    assert all((e["t_ms"] or 0) < HALF for e in events2.values())
    assert events2[tagged["id"]]["t_ms"] is None  # its place in the video went with the file
    match = (await api.get(base)).json()
    assert [v["part"] for v in match["videos"]] == [1]
    assert (await api.get(f"{base}/graphics")).json()["parts"] == []

    # deleting the first part of two moves the other one to the start
    third = await upload(api, ids, match_id, b"c" * 100, name="halbzeit2b.mp4")
    await _ingest(api, third["id"], HALF)
    await _analyse(api, third["id"], events=SECOND)
    assert (await api.get(f"{base}/parts")).json()[1]["video_id"] == third["id"]
    assert (await api.delete(f"/v1/orgs/{org}/videos/{first}")).status_code == 204
    events3 = (await api.get(f"{base}/events")).json()
    assert sorted(e["t_ms"] for e in events3 if e["source"] == "heuristic") == [
        4000,
        50_000,
        56_000,
    ]


async def test_the_same_file_twice_is_said(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    m = await new_match(api, ids)
    first = await upload(api, ids, m["id"], b"a" * 100, name="halbzeit1.mp4")
    r = await api.post(
        f"/v1/orgs/{org}/matches/{m['id']}/videos",
        json={"filename": "halbzeit1.mp4", "size_bytes": 100, "content_type": "video/mp4"},
    )
    assert r.status_code == 409 and r.json()["type"].endswith("same-file")
    await _ingest(api, first["id"], HALF, checksum="c" * 64)
    # a copy with another name: found by its content once it is processed
    copy = await upload(api, ids, m["id"], b"a" * 100, name="kopie.mp4")
    await _ingest(api, copy["id"], HALF, checksum="c" * 64)
    match = (await api.get(f"/v1/orgs/{org}/matches/{m['id']}")).json()
    dup = next(v for v in match["videos"] if v["id"] == copy["id"])
    assert dup["duplicate_of"] == first["id"] and dup["part"] is None
    assert match["status"] == "ready"
    assert len([j for j in _jobs(api).jobs if j[1] == ANALYSIS]) == 1  # no second analysis


async def test_a_failed_second_half_leaves_the_first_usable(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    match_id, _first, second = await _two_halves(api, ids)
    base = f"/v1/orgs/{org}/matches/{match_id}"
    job, _ = _job_of(api, second, ANALYSIS)
    r = await api.http.post(
        f"/internal/jobs/{job}",
        headers=_token(api),
        json={"status": "failed", "progress": 0.4, "error": "RuntimeError: boom"},
    )
    assert r.status_code == 200
    g = (await api.get(f"{base}/graphics")).json()
    assert g["analysis"] == "ready"
    assert [p["analysis"] for p in g["parts"]] == ["ready", "failed"]
    assert any(e["source"] == "heuristic" for e in (await api.get(f"{base}/events")).json())
    # «Erneut versuchen» for that part only
    r = await api.post(f"/v1/orgs/{org}/videos/{second}/analysis")
    assert r.status_code == 202
    assert _job_of(api, second, ANALYSIS)[0] != job
    assert (await api.post(f"/v1/orgs/{org}/videos/{second}/analysis")).status_code == 409
    assert (await api.get(f"{base}/graphics")).json()["analysis"] == "running"


async def test_a_short_accidental_part_is_not_the_second_half(
    make_api: Callable[[], Api],
) -> None:
    api = make_api()
    ids = await setup_club(api)
    m = await new_match(api, ids)
    first = await upload(api, ids, m["id"], b"a" * 100, name="spiel.mp4")
    await _ingest(api, first["id"], 2 * HALF)
    await _analyse(api, first["id"], events=FIRST)
    short = await upload(api, ids, m["id"], b"s" * 100, name="versehen.mp4")
    await _ingest(api, short["id"], 5000)
    _, payload = _job_of(api, short["id"], ANALYSIS)
    assert "side_hint" not in payload
    match = (await api.get(f"/v1/orgs/{ids['org']}/matches/{m['id']}")).json()
    part = next(v for v in match["videos"] if v["id"] == short["id"])
    assert part["part"] == 2 and part["duration_s"] == 5.0


async def test_the_second_half_asks_its_court_only_when_not_carried_over(
    make_api: Callable[[], Api],
) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    match_id, first, second = await _two_halves(api, ids)
    base = f"/v1/orgs/{org}/matches/{match_id}"
    cal = {
        "homography": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
        "image_size": [1280, 720],
        "confidence": 1.0,
        "reprojection_px": 0.0,
        "source": "heuristic",
    }
    # the first half's court is confirmed; the second half's analysis found its own court
    await _analyse(
        api,
        first,
        again=True,
        events=FIRST,
        calibration=cal,
        chunks=1,
        chunk_ms=30_000,
        panorama={"width": 1280, "height": 720},
    )
    assert (await api.post(f"/v1/orgs/{org}/videos/{first}/calibration/confirm")).status_code == 200
    payload = await _analyse(api, second, calibration=cal, chunks=1, chunk_ms=30_000)
    checks = (await api.get(f"{base}/graphics")).json()["checks"]
    field = [c for c in checks if c["kind"] == "field"]
    assert [(c["id"], c["copy_from"]) for c in field] == [(second, first)]
    # the court of the first half for the second: a new run of the second half's analysis with
    # the first half's court as the hall to match
    url = f"/v1/orgs/{org}/videos/{second}/calibration/from/{first}"
    assert (await api.post(url)).status_code == 202
    _, rerun = _job_of(api, second, ANALYSIS)
    assert [r["video_id"] for r in rerun["hall_references"]] == [first]
    assert rerun["calibration_points"] is None
    same = f"/v1/orgs/{org}/videos/{first}/calibration/from/{first}"
    assert (await api.post(same)).status_code == 422
    job, _ = _job_of(api, second, ANALYSIS)
    await _finish(api, job, {"tracks": _tracks(), "detector": "model", "calibration": cal})

    # carried over from the first half by the worker: not asked
    assert (await api.post(f"/v1/orgs/{org}/videos/{second}/analysis")).status_code == 202
    job, auto = _job_of(api, second, ANALYSIS)
    # the other half's confirmed court is tried first on every run of this part
    assert [r["video_id"] for r in auto["hall_references"]] == [first]
    info = {"method": "hall", "reference_video_id": first, "floor_inliers": 80}
    await _finish(
        api,
        job,
        {
            "tracks": _tracks(),
            "detector": "model",
            "calibration": cal,
            "calibration_info": info,
            "chunks": 1,
            "chunk_ms": 30_000,
        },
    )
    checks = (await api.get(f"{base}/graphics")).json()["checks"]
    assert [c for c in checks if c["kind"] == "field"] == []
    assert payload["asset_id"] == second


async def test_the_player_plays_both_halves(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    match_id, first, second = await _two_halves(api, ids)
    storage: MemoryStorage = api.app.state.storage
    match = (await api.get(f"/v1/orgs/{org}/matches/{match_id}")).json()
    assert match["videos"][0]["id"] == first
    variant = (
        "#EXTM3U\n#EXT-X-VERSION:7\n#EXT-X-TARGETDURATION:{d}\n#EXT-X-MEDIA-SEQUENCE:0\n"
        '#EXT-X-PLAYLIST-TYPE:VOD\n#EXT-X-INDEPENDENT-SEGMENTS\n#EXT-X-MAP:URI="init.mp4"\n'
        "#EXTINF:4.000000,\nseg_00000.m4s\n#EXTINF:{d}.000000,\nseg_00001.m4s\n#EXT-X-ENDLIST\n"
    )
    for vid, heights, d in ((first, ["720p", "1080p"], 4), (second, ["720p"], 6)):
        prefix = f"{ids['org']}/{match_id}/{vid}/"
        master = "#EXTM3U\n" + "".join(
            f"#EXT-X-STREAM-INF:BANDWIDTH=1\n{h}/index.m3u8\n" for h in heights
        )
        await storage.put("videos", prefix + "hls/master.m3u8", master.encode(), "x")
        for h in heights:
            await storage.put(
                "videos", prefix + f"hls/{h}/index.m3u8", variant.format(d=d).encode(), "x"
            )
        vtt = "WEBVTT\n\n00:00:00.000 --> 00:00:10.000\nthumbs.jpg#xywh=0,0,160,90\n"
        await storage.put("videos", prefix + "thumbs.vtt", vtt.encode(), "text/vtt")

    media = f"/v1/orgs/{org}/videos/{first}/media"
    joined = (await api.get(f"{media}/hls/1080p/index.m3u8")).text
    lines = joined.splitlines()
    assert lines.count("#EXT-X-DISCONTINUITY") == 1
    assert "#EXT-X-TARGETDURATION:6" in lines
    assert lines.count("#EXT-X-ENDLIST") == 1
    # the second file has no 1080p: its nearest variant
    assert f"../../../../{second}/media/hls/720p/seg_00001.m4s" in lines
    assert f'#EXT-X-MAP:URI="../../../../{second}/media/hls/720p/init.mp4"' in lines
    assert lines[lines.index("#EXT-X-DISCONTINUITY") - 1] == "seg_00001.m4s"
    vtt = (await api.get(f"{media}/thumbs.vtt")).text
    assert "00:30:00.000 --> 00:30:10.000" in vtt
    assert f"../../{second}/media/thumbs.jpg#xywh=0,0,160,90" in vtt
    # the master and the second file alone are served as stored
    assert (await api.get(f"{media}/hls/master.m3u8")).text.count("index.m3u8") == 2
    alone = (await api.get(f"/v1/orgs/{org}/videos/{second}/media/hls/720p/index.m3u8")).text
    assert "#EXT-X-DISCONTINUITY" not in alone

    # the native apps: each file with its own signed path
    signed = (await api.post(f"/v1/orgs/{org}/videos/{first}/media-token")).json()["base"]
    text = (await api.http.get(f"{signed}hls/720p/index.m3u8")).text
    other = next(x for x in text.splitlines() if second in x and x.endswith("seg_00000.m4s"))
    assert other.startswith(f"../../../../{second}/") and "/hls/720p/" in other
    seg_url = signed.rsplit("/", 3)[0] + "/" + other.replace("../../../../", "")
    await storage.put(
        "videos", f"{ids['org']}/{match_id}/{second}/hls/720p/seg_00000.m4s", b"seg", "x"
    )
    assert (await api.http.get(seg_url)).content == b"seg"


async def test_swap_and_swap_back_gives_the_same_times(make_api: Callable[[], Api]) -> None:
    """Moving the rows with the parts is exact: swapped and swapped back, every time is where it
    was (events, candidates, possessions, clips, the throw-offs)."""
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    match_id, first, second = await _two_halves(api, ids)
    base = f"/v1/orgs/{org}/matches/{match_id}"
    await _analyse(api, second, events=SECOND, goal_candidates={"candidates": [_cand(52_000, 1)]})
    await api.post(
        f"/v1/orgs/{org}/clips",
        json={"match_id": match_id, "start_ms": HALF + 10_000, "end_ms": HALF + 20_000},
    )

    async def times() -> dict[str, Any]:
        return {
            "events": sorted(
                (e["id"], e["t_ms"]) for e in (await api.get(f"{base}/events")).json()
            ),
            "cands": sorted(
                (c["id"], c["t_ms"], c["goal_ms"])
                for c in (await api.get(f"{base}/goal-candidates")).json()["candidates"]
            ),
            "phases": sorted(
                (p["start_ms"], p["end_ms"])
                for p in (await api.get(f"{base}/possessions")).json()["phases"]
            ),
            "clips": sorted(
                (c["start_ms"], c["end_ms"]) for c in (await api.get(f"{base}/clips")).json()
            ),
            "kickoff": (await api.get(base)).json()["kickoff_ms"],
        }

    before = await times()
    url = f"{base}/parts"
    await api.put(url, json={"video_ids": [second, first]})
    swapped = await times()
    assert swapped != before
    await api.put(url, json={"video_ids": [first, second]})
    assert await times() == before
    # the same order again changes nothing
    await api.put(url, json={"video_ids": [first, second]})
    assert await times() == before


async def test_a_reel_cuts_each_scene_from_its_own_half(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    match_id, first, second = await _two_halves(api, ids)
    await _analyse(api, second, events=SECOND)
    org = ids["org"]
    base = f"/v1/orgs/{org}/matches/{match_id}"
    for t in (20_000, 200_000, HALF + 30_000, HALF + 300_000):
        await api.post(
            f"{base}/events", json={"type": "shot", "side": "own", "outcome": "goal", "t_ms": t}
        )
    r = await api.post(f"{base}/highlights", json={"format": "16x9"})
    assert r.status_code == 202, r.text
    job = [j for j in _jobs(api).jobs if j[1] == "handball_worker.reels.run_highlight_reel"][-1]
    payload = job[3]["payload"]
    assert len(payload["sources"]) == 2
    assert payload["sources"][0]["proxy_key"].endswith(f"{first}/proxy.mp4")
    assert payload["sources"][1]["proxy_key"].endswith(f"{second}/proxy.mp4")
    later = [c for c in payload["clips"] if c["source"] == 1]
    assert later and all(0 <= c["in_ms"] < HALF for c in later)

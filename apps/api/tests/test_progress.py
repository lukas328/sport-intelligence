"""The progress of uploads and processing (K6, K13, B4): steps, time left, «hängt?», watchdog."""

from __future__ import annotations

import re
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import asyncpg
import pytest

from handball_api.core.storage import MemoryStorage
from handball_api.models import ProcessingJob, VideoAsset
from handball_api.models.enums import JobStatus, VideoRole, VideoStatus
from handball_api.services import progress
from handball_api.services.progress import Throughput, UploadParts, file_progress, match_summary

from .conftest import Api, setup_club
from .test_matches import new_match, upload
from .test_video_parts import HALF, _ingest, _jobs, _token

pytestmark = pytest.mark.usefixtures("clean_db")

NOW = datetime(2026, 11, 16, 18, 0, tzinfo=UTC)
GB = 1024**3
ANALYSIS = "handball_gpu_worker.analysis.run_analysis"


@pytest.fixture(autouse=True)
def _fresh_pace() -> None:
    progress.reset_cache()


def _asset(status: VideoStatus, **kw: Any) -> VideoAsset:
    a = VideoAsset(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        match_id=uuid.uuid4(),
        role=kw.pop("role", VideoRole.MAIN),
        status=status,
        filename="spiel.mp4",
        content_type="video/mp4",
        size_bytes=kw.pop("size_bytes", 4 * GB),
        storage_key="k",
        part_size=16 * 1024**2,
        **kw,
    )
    a.created_at = kw.get("created_at") or NOW - timedelta(minutes=30)
    return a


def _job(kind: str, status: JobStatus, **kw: Any) -> ProcessingJob:
    j = ProcessingJob(
        id=uuid.uuid4(),
        kind=kind,
        status=status,
        pipeline_version="0.2.0",
        progress=kw.pop("progress", 0.0),
        stages=kw.pop("stages", {}),
        **kw,
    )
    j.created_at = kw.get("created_at") or NOW - timedelta(minutes=20)
    return j


def test_upload_measures_its_pace_and_says_when_it_stopped() -> None:
    a = _asset(VideoStatus.UPLOADING, size_bytes=1000 * 1024**2, created_at=NOW)
    a.created_at = NOW - timedelta(minutes=10)
    running = file_progress(
        a, [], NOW, Throughput(), UploadParts(250 * 1024**2, NOW - timedelta(seconds=20))
    )
    assert running is not None
    assert (running.stage, running.state) == ("upload", "running")
    assert running.fraction == 0.25 and running.eta_basis == "measured"
    # a quarter in 9 min 40 s: about 29 minutes for the rest
    assert running.eta_s is not None and 1700 < running.eta_s < 1800
    stopped = file_progress(
        a, [], NOW, Throughput(), UploadParts(250 * 1024**2, NOW - timedelta(minutes=7))
    )
    assert stopped is not None and stopped.state == "interrupted"
    assert stopped.eta_s is None and stopped.idle_s == 420


def test_ingest_from_history_then_from_its_own_pace() -> None:
    a = _asset(VideoStatus.PROCESSING, size_bytes=4 * GB)
    pace = Throughput(analysis_per_video_s=2.0, ingest_per_gb=600.0)
    queued = file_progress(a, [_job("ingest", JobStatus.QUEUED)], NOW, pace)
    assert queued is not None and (queued.stage, queued.state) == ("ingest", "queued")
    assert queued.eta_s == 2400 and queued.eta_basis == "history"
    early = _job(
        "ingest",
        JobStatus.RUNNING,
        progress=0.02,
        started_at=NOW - timedelta(minutes=2),
        heartbeat_at=NOW - timedelta(seconds=30),
    )
    f = file_progress(a, [early], NOW, pace)
    assert f is not None and f.eta_basis == "history" and f.eta_s == 2400 - 120
    later = _job(
        "ingest",
        JobStatus.RUNNING,
        progress=0.5,
        started_at=NOW - timedelta(minutes=30),
        heartbeat_at=NOW - timedelta(seconds=30),
        stages={"transcode": {"status": "running"}},
    )
    f = file_progress(a, [later], NOW, pace)
    assert f is not None and f.eta_basis == "measured" and f.eta_s == 1800
    assert f.step == "transcode" and f.overall == pytest.approx(0.1 + 0.3 * 0.5)


def test_no_estimate_without_pace_or_history() -> None:
    a = _asset(VideoStatus.PROCESSING)
    f = file_progress(a, [_job("ingest", JobStatus.QUEUED)], NOW, Throughput())
    assert f is not None and f.eta_s is None and f.eta_basis is None


def test_a_silent_job_is_stalled_with_the_time_of_the_restart() -> None:
    a = _asset(VideoStatus.READY, duration_s=3600)
    last = NOW - timedelta(minutes=14)
    job = _job(
        "analysis",
        JobStatus.RUNNING,
        progress=0.4,
        started_at=NOW - timedelta(hours=2),
        heartbeat_at=last,
    )
    f = file_progress(a, [_job("ingest", JobStatus.SUCCEEDED), job], NOW, Throughput())
    assert f is not None and (f.stage, f.state) == ("analysis", "stalled")
    assert f.idle_s == 14 * 60 and f.eta_s is None
    assert f.restart_at == last + timedelta(seconds=progress.RESTART_AFTER_S + 600)


def test_two_halves_one_after_the_other() -> None:
    """B4: the second half waits for the first; its finish counts from the first one's."""
    pace = Throughput(analysis_per_video_s=1.0, ingest_per_gb=600.0)
    first = _asset(VideoStatus.READY, duration_s=1800)
    second = _asset(VideoStatus.READY, duration_s=1800, analysis={"waiting_job": "x"})
    run = _job(
        "analysis",
        JobStatus.RUNNING,
        progress=0.5,
        started_at=NOW - timedelta(minutes=30),
        heartbeat_at=NOW,
    )
    files = [
        file_progress(first, [run], NOW, pace, part=1, half=1),
        file_progress(second, [_job("analysis", JobStatus.QUEUED)], NOW, pace, part=2, half=2),
    ]
    assert files[0] is not None and files[1] is not None
    assert files[1].state == "waiting" and files[1].finish_s == 1800
    from handball_api.models import Match

    m = Match(id=uuid.uuid4(), team_id=uuid.uuid4(), kind="match", is_home=True, kickoff_at=NOW)
    summary = match_summary(m, "TV Gegner", [f for f in files if f], [run], NOW)
    assert summary is not None and summary.state == "running" and summary.stage == "analysis"
    assert summary.eta_s == 1800 + 1800  # 30 min left of the first, then 30 for the second


async def test_progress_through_upload_ingest_and_analysis(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    m = await new_match(api, ids)
    storage: MemoryStorage = api.app.state.storage
    r = await api.post(
        f"/v1/orgs/{org}/matches/{m['id']}/videos",
        json={"filename": "spiel.mp4", "size_bytes": 40 * 1024**2, "content_type": "video/mp4"},
    )
    vid = r.json()["video"]["id"]
    urls = (await api.post(f"/v1/orgs/{org}/videos/{vid}/parts", json={"numbers": [1]})).json()
    upload_id = re.search(r"uploadId=(\w+)", urls[0]["url"]).group(1)  # type: ignore[union-attr]
    storage.upload_part(upload_id, 1, b"x" * 1000)

    shown = (await api.get(f"/v1/orgs/{org}/progress")).json()
    assert [p["match_id"] for p in shown] == [m["id"]]
    file = shown[0]["files"][0]
    assert (shown[0]["stage"], file["stage"], file["state"]) == ("upload", "upload", "running")
    assert file["uploaded_bytes"] == 1000 and file["size_bytes"] == 40 * 1024**2

    # a whole file: einlesen, then analysieren
    m2 = await new_match(api, ids, opponent_name="SG Zwei")
    video = await upload(api, ids, m2["id"], b"v" * 100)
    detail = (await api.get(f"/v1/orgs/{org}/matches/{m2['id']}")).json()
    assert detail["progress"]["stage"] == "ingest"
    assert detail["progress"]["files"][0]["state"] == "queued"
    ingest = [j for j in _jobs(api).jobs if j[3].get("asset_id") == video["id"]][-1][2]
    r = await api.http.post(
        f"/internal/jobs/{ingest}",
        headers=_token(api),
        json={"status": "running", "progress": 0.3, "stage": "transcode"},
    )
    assert r.status_code == 200
    detail = (await api.get(f"/v1/orgs/{org}/matches/{m2['id']}")).json()
    f = detail["progress"]["files"][0]
    assert (f["stage"], f["state"], f["fraction"]) == ("ingest", "running", 0.3)
    assert f["last_activity_at"] is not None  # the report is the heartbeat
    await _ingest(api, video["id"], HALF)
    detail = (await api.get(f"/v1/orgs/{org}/matches/{m2['id']}")).json()
    assert detail["progress"]["stage"] == "analysis"
    analysis = [j for j in _jobs(api).jobs if j[1] == ANALYSIS][-1][2]
    r = await api.http.post(
        f"/internal/jobs/{analysis}",
        headers=_token(api),
        json={"status": "succeeded", "progress": 1, "result": {"tracks": []}},
    )
    assert r.status_code == 200, r.text
    detail = (await api.get(f"/v1/orgs/{org}/matches/{m2['id']}")).json()
    assert detail["progress"]["state"] == "done" and detail["progress"]["finished_at"]


async def test_watchdog_restarts_a_silent_job_once_then_ends_it(
    make_api: Callable[[], Api], owner_conn: asyncpg.Connection
) -> None:
    api = make_api()
    ids = await setup_club(api)
    m = await new_match(api, ids)
    video = await upload(api, ids, m["id"], b"v" * 100)
    first = [j for j in _jobs(api).jobs if j[3].get("asset_id") == video["id"]][-1][2]
    await api.http.post(
        f"/internal/jobs/{first}", headers=_token(api), json={"status": "running", "progress": 0.2}
    )

    async def silence(job_id: str) -> None:
        await owner_conn.execute(
            "UPDATE processing_jobs SET heartbeat_at = now() - interval '45 minutes' WHERE id = $1",
            uuid.UUID(job_id),
        )

    await silence(first)
    r = await api.http.post("/internal/watchdog", headers=_token(api))
    assert r.status_code == 200
    assert r.json() == {"restarted": 1, "failed": 0, "requeued": 0, "abandoned": 0}
    second = [j for j in _jobs(api).jobs if j[3].get("asset_id") == video["id"]][-1][2]
    assert second != first
    status = await owner_conn.fetchval(
        "SELECT status FROM processing_jobs WHERE id = $1", uuid.UUID(first)
    )
    assert status == "cancelled"
    # a late report of the replaced job changes nothing
    await api.http.post(
        f"/internal/jobs/{first}", headers=_token(api), json={"status": "running", "progress": 0.5}
    )
    detail = (await api.get(f"/v1/orgs/{ids['org']}/matches/{m['id']}")).json()
    assert detail["progress"]["files"][0]["restarted"] is True
    await api.http.post(
        f"/internal/jobs/{second}", headers=_token(api), json={"status": "running", "progress": 0.1}
    )
    await silence(second)
    r = await api.http.post("/internal/watchdog", headers=_token(api))
    assert r.json() == {"restarted": 0, "failed": 1, "requeued": 0, "abandoned": 0}
    detail = (await api.get(f"/v1/orgs/{ids['org']}/matches/{m['id']}")).json()
    assert detail["progress"]["state"] == "failed"
    assert (await api.http.post("/internal/watchdog")).status_code in (403, 422)


async def test_watchdog_enqueues_again_a_job_redis_lost(
    make_api: Callable[[], Api], owner_conn: asyncpg.Connection
) -> None:
    """Redis runs without persistence: a restart (with every deploy on staging, 17.11.) wipes out
    the jobs that were only waiting. The watchdog finds them missing from the queue and starts
    the step again; a job still in the queue, or a fresh one, is left alone."""
    api = make_api()
    ids = await setup_club(api)
    m = await new_match(api, ids)
    video = await upload(api, ids, m["id"], b"v" * 100)
    first = [j for j in _jobs(api).jobs if j[3].get("asset_id") == video["id"]][-1][2]
    r = await api.http.post("/internal/watchdog", headers=_token(api))
    assert r.json()["requeued"] == 0  # fresh and still in the queue
    await owner_conn.execute(
        "UPDATE processing_jobs SET created_at = now() - interval '20 minutes' WHERE id = $1",
        uuid.UUID(first),
    )
    r = await api.http.post("/internal/watchdog", headers=_token(api))
    assert r.json()["requeued"] == 0  # waiting long, but the queue still has it
    _jobs(api).lost.add(first)
    r = await api.http.post("/internal/watchdog", headers=_token(api))
    assert r.json() == {"restarted": 0, "failed": 0, "requeued": 1, "abandoned": 0}
    second = [j for j in _jobs(api).jobs if j[3].get("asset_id") == video["id"]][-1][2]
    assert second != first
    row = await owner_conn.fetchrow(
        "SELECT status, error FROM processing_jobs WHERE id = $1", uuid.UUID(first)
    )
    assert (row["status"], row["error"]) == ("cancelled", "lost from the queue")
    detail = (await api.get(f"/v1/orgs/{ids['org']}/matches/{m['id']}")).json()
    assert detail["progress"]["files"][0]["state"] == "queued"


async def test_progress_needs_access_to_the_team(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    m = await new_match(api, ids)
    await upload(api, ids, m["id"], b"v" * 100)
    other = make_api()
    await setup_club(other, email="other@hc-else.ch")
    assert (await other.get(f"/v1/orgs/{ids['org']}/progress")).status_code in (403, 404)


async def test_the_same_file_again_continues_its_unfinished_upload(
    make_api: Callable[[], Api],
) -> None:
    """L4: after a reload (or on another device) the same file continues where it stopped."""
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    m = await new_match(api, ids)
    body = {"filename": "spiel.mp4", "size_bytes": 40 * 1024**2, "content_type": "video/mp4"}
    first = (await api.post(f"/v1/orgs/{org}/matches/{m['id']}/videos", json=body)).json()
    assert first["resumed"] is False
    again = await api.post(f"/v1/orgs/{org}/matches/{m['id']}/videos", json=body)
    assert again.status_code == 201 and again.json()["resumed"] is True
    assert again.json()["video"]["id"] == first["video"]["id"]
    assert again.json()["part_count"] == first["part_count"]
    # the storage forgot the parts: a new upload, the old one is over
    storage: MemoryStorage = api.app.state.storage
    storage.uploads.clear()
    fresh = (await api.post(f"/v1/orgs/{org}/matches/{m['id']}/videos", json=body)).json()
    assert fresh["resumed"] is False and fresh["video"]["id"] != first["video"]["id"]
    videos = (await api.get(f"/v1/orgs/{org}/matches/{m['id']}")).json()["videos"]
    old = next(v for v in videos if v["id"] == first["video"]["id"])
    assert old["status"] == "failed"

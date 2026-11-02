from __future__ import annotations

import re
import uuid
from collections.abc import Callable
from typing import Any

import pytest

from handball_api.core.email import MemoryEmailSender
from handball_api.core.jobs import MemoryEventBus, MemoryJobQueue
from handball_api.core.storage import MemoryStorage

from .conftest import Api, setup_club

pytestmark = pytest.mark.usefixtures("clean_db")

MB = 1024 * 1024


async def new_match(api: Api, ids: dict[str, Any], **kw: Any) -> dict[str, Any]:
    body = {"opponent_name": "TV Gegner", "kickoff_at": "2026-11-07T18:00:00+01:00", **kw}
    r = await api.post(f"/v1/orgs/{ids['org']}/teams/{ids['team']}/matches", json=body)
    assert r.status_code == 201, r.text
    return dict(r.json())


async def upload(
    api: Api, ids: dict[str, Any], match_id: str, data: bytes, name: str = "spiel.mp4"
) -> dict[str, Any]:
    storage: MemoryStorage = api.app.state.storage
    org = ids["org"]
    r = await api.post(
        f"/v1/orgs/{org}/matches/{match_id}/videos",
        json={"filename": name, "size_bytes": len(data), "content_type": "video/mp4"},
    )
    assert r.status_code == 201, r.text
    up = r.json()
    vid, size = up["video"]["id"], up["part_size"]
    numbers = list(range(1, up["part_count"] + 1))
    urls = (await api.post(f"/v1/orgs/{org}/videos/{vid}/parts", json={"numbers": numbers})).json()
    parts = []
    for u in urls:
        upload_id = re.search(r"uploadId=(\w+)", u["url"]).group(1)  # type: ignore[union-attr]
        n = u["number"]
        etag = storage.upload_part(upload_id, n, data[(n - 1) * size : n * size])
        parts.append({"number": n, "etag": etag})
    done = await api.post(f"/v1/orgs/{org}/videos/{vid}/complete", json={"parts": parts})
    assert done.status_code == 200, done.text
    return dict(done.json())


async def test_opponents_and_match_crud(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    m = await new_match(api, ids, competition="3. Liga", is_home=False)
    assert m["opponent"]["name"] == "TV Gegner"
    assert m["status"] == "scheduled"
    assert m["season_id"] == ids["season"]
    # the same opponent name is reused
    m2 = await new_match(
        api, ids, opponent_name="tv gegner", kickoff_at="2026-11-14T18:00:00+01:00"
    )
    assert m2["opponent"]["id"] == m["opponent"]["id"]
    opps = (await api.get(f"/v1/orgs/{ids['org']}/opponents")).json()
    assert len(opps) == 1
    upd = await api.patch(
        f"/v1/orgs/{ids['org']}/opponents/{opps[0]['id']}", json={"primary_color": "#123456"}
    )
    assert upd.json()["primary_color"] == "#123456"
    lst = (await api.get(f"/v1/orgs/{ids['org']}/teams/{ids['team']}/matches")).json()
    assert [x["kickoff_at"][:10] for x in lst] == ["2026-11-14", "2026-11-07"]
    assert lst[0]["has_video"] is False
    r = await api.patch(
        f"/v1/orgs/{ids['org']}/matches/{m['id']}", json={"score_own": 28, "score_opponent": 25}
    )
    assert (r.json()["score_own"], r.json()["score_opponent"]) == (28, 25)
    bad = await api.post(
        f"/v1/orgs/{ids['org']}/teams/{ids['team']}/matches",
        json={"kickoff_at": "2026-11-07T18:00:00", "opponent_name": "X"},
    )
    assert bad.status_code == 422
    assert (await api.delete(f"/v1/orgs/{ids['org']}/matches/{m['id']}")).status_code == 204
    assert (await api.get(f"/v1/orgs/{ids['org']}/matches/{m['id']}")).status_code == 404


async def test_upload_resume_complete_and_ingest(make_api: Callable[[], Api]) -> None:
    api = make_api()
    api.app.state.settings.upload_part_size = 5 * MB
    ids = await setup_club(api)
    m = await new_match(api, ids)
    org = ids["org"]
    data = bytes(range(256)) * (12 * MB // 256)  # 12 MB -> 3 parts
    r = await api.post(
        f"/v1/orgs/{org}/matches/{m['id']}/videos",
        json={"filename": "Spiel.MOV", "size_bytes": len(data), "content_type": "video/quicktime"},
    )
    up = r.json()
    assert up["part_count"] == 3
    vid = up["video"]["id"]
    storage: MemoryStorage = api.app.state.storage
    urls = (
        await api.post(f"/v1/orgs/{org}/videos/{vid}/parts", json={"numbers": [1, 2, 3]})
    ).json()
    upload_id = re.search(r"uploadId=(\w+)", urls[0]["url"]).group(1)  # type: ignore[union-attr]
    storage.upload_part(upload_id, 1, data[: 5 * MB])
    # browser closes: on resume the client asks which parts exist
    parts = (await api.get(f"/v1/orgs/{org}/videos/{vid}/parts")).json()
    assert [p["number"] for p in parts] == [1]
    assert (
        await api.post(f"/v1/orgs/{org}/videos/{vid}/parts", json={"numbers": [4]})
    ).status_code == 422
    incomplete = await api.post(
        f"/v1/orgs/{org}/videos/{vid}/complete",
        json={"parts": [{"number": 1, "etag": parts[0]["etag"]}]},
    )
    assert incomplete.status_code == 422
    e2 = storage.upload_part(upload_id, 2, data[5 * MB : 10 * MB])
    e3 = storage.upload_part(upload_id, 3, data[10 * MB :])
    done = await api.post(
        f"/v1/orgs/{org}/videos/{vid}/complete",
        json={
            "parts": [
                {"number": 1, "etag": parts[0]["etag"]},
                {"number": 2, "etag": e2},
                {"number": 3, "etag": e3},
            ]
        },
    )
    assert done.json()["status"] == "processing"
    assert (
        await api.post(f"/v1/orgs/{org}/videos/{vid}/parts", json={"numbers": [1]})
    ).status_code == 409
    jobs: MemoryJobQueue = api.app.state.jobs
    queue, func, job_id, kwargs = jobs.jobs[-1]
    assert (queue, func) == ("pipeline", "handball_worker.ingest.run_ingest")
    assert kwargs["key"].endswith("/original.mov")
    match = (await api.get(f"/v1/orgs/{org}/matches/{m['id']}")).json()
    assert match["status"] == "processing"
    assert match["jobs"][0]["status"] == "queued"

    # worker reports progress and the result
    token = {"x-internal-token": api.app.state.settings.internal_token.get_secret_value()}
    assert (
        await api.http.post(
            f"/internal/jobs/{job_id}",
            json={"status": "running", "progress": 0.4},
            headers={"x-internal-token": "nope"},
        )
    ).status_code == 403
    r = await api.http.post(
        f"/internal/jobs/{job_id}",
        headers=token,
        json={"status": "running", "progress": 0.4, "stages": {"transcode": {"status": "running"}}},
    )
    assert r.json()["progress"] == 0.4
    prefix = kwargs["prefix"]
    await storage.put(
        "videos", prefix + "hls/master.m3u8", b"#EXTM3U\n", "application/vnd.apple.mpegurl"
    )
    await storage.put("videos", prefix + "poster.jpg", b"\xff\xd8\xff", "image/jpeg")
    r = await api.http.post(
        f"/internal/jobs/{job_id}",
        headers=token,
        json={
            "status": "succeeded",
            "progress": 1,
            "result": {
                "checksum_sha256": "ab" * 32,
                "duration_s": 3600.5,
                "fps": 50,
                "width": 3840,
                "height": 2160,
                "codec": "hevc",
                "hls_prefix": prefix + "hls/",
                "poster_key": prefix + "poster.jpg",
                "proxy_key": prefix + "proxy.mp4",
                "quality_report": {"overall": "ok", "checks": [], "thumbnails": True},
            },
        },
    )
    assert r.json()["status"] == "succeeded"
    events: MemoryEventBus = api.app.state.events
    assert [e["status"] for _, e in events.published] == ["running", "succeeded"]
    match = (await api.get(f"/v1/orgs/{org}/matches/{m['id']}")).json()
    assert match["status"] == "ready"
    v = match["videos"][0]
    assert (v["status"], v["width"], v["has_hls"], v["has_thumbnails"]) == (
        "ready",
        3840,
        True,
        True,
    )
    # duplicate callbacks are ignored
    again = await api.http.post(
        f"/internal/jobs/{job_id}", headers=token, json={"status": "failed", "progress": 0}
    )
    assert again.json()["status"] == "succeeded"

    # media files are served with access control; originals and proxies are never served
    pl = await api.get(f"/v1/orgs/{org}/videos/{vid}/media/hls/master.m3u8")
    assert pl.headers["content-type"] == "application/vnd.apple.mpegurl"
    assert (await api.get(f"/v1/orgs/{org}/videos/{vid}/media/poster.jpg")).status_code == 200
    for path in ("proxy.mp4", "original.mov", "../x.jpg", "hls/missing.m3u8", "a.exe"):
        assert (await api.get(f"/v1/orgs/{org}/videos/{vid}/media/{path}")).status_code == 404, path
    other = make_api()
    await setup_club(other, "x@hc-test.ch")
    assert (
        await other.get(f"/v1/orgs/{org}/videos/{vid}/media/hls/master.m3u8")
    ).status_code == 404

    # reprocess and offset
    assert (await api.post(f"/v1/orgs/{org}/videos/{vid}/reprocess")).status_code == 202
    assert (await api.patch(f"/v1/orgs/{org}/videos/{vid}", json={"time_offset_ms": -1200})).json()[
        "time_offset_ms"
    ] == -1200

    # deleting the match removes all stored objects of it
    assert any(k[1].startswith(f"{org}/{m['id']}/") for k in storage.objects)
    await api.delete(f"/v1/orgs/{org}/matches/{m['id']}")
    assert not any(k[1].startswith(f"{org}/{m['id']}/") for k in storage.objects)


async def test_failed_ingest_marks_match(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    m = await new_match(api, ids)
    await upload(api, ids, m["id"], b"x" * 1000)
    job_id = api.app.state.jobs.jobs[-1][2]
    token = {"x-internal-token": api.app.state.settings.internal_token.get_secret_value()}
    await api.http.post(
        f"/internal/jobs/{job_id}",
        headers=token,
        json={"status": "failed", "progress": 0.1, "error": "no video stream"},
    )
    match = (await api.get(f"/v1/orgs/{ids['org']}/matches/{m['id']}")).json()
    assert match["status"] == "failed"
    assert match["videos"][0]["error"] == "no video stream"
    assert (
        await api.http.post(
            f"/internal/jobs/{uuid.uuid4()}",
            headers=token,
            json={"status": "running", "progress": 0},
        )
    ).status_code == 404


async def test_upload_validation(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    m = await new_match(api, ids)
    url = f"/v1/orgs/{ids['org']}/matches/{m['id']}/videos"
    assert (await api.post(url, json={"filename": "x.exe", "size_bytes": 10})).status_code == 415
    assert (
        await api.post(url, json={"filename": "x.mp4", "size_bytes": 10**15})
    ).status_code == 413
    assert (
        await api.post(
            url, json={"filename": "x.mp4", "size_bytes": 10, "content_type": "text/html"}
        )
    ).status_code == 422
    r = await api.post(url, json={"filename": "x.mp4", "size_bytes": 10})
    vid = r.json()["video"]["id"]
    assert (await api.delete(f"/v1/orgs/{ids['org']}/videos/{vid}")).status_code == 204


async def test_link_import(make_api: Callable[[], Api], monkeypatch: pytest.MonkeyPatch) -> None:
    api = make_api()
    ids = await setup_club(api)
    m = await new_match(api, ids)
    url = f"/v1/orgs/{ids['org']}/matches/{m['id']}/videos/import"
    for bad in (
        "http://example.com/a.mp4",
        "https://127.0.0.1/a.mp4",
        "https://10.0.0.1/a.mp4",
        "https://user:pw@example.com/a.mp4",
        "https://example.com:8443/a.mp4",
    ):
        r = await api.post(url, json={"url": bad})
        assert r.status_code == 422, bad
    import handball_api.services.videos as v

    monkeypatch.setattr(v, "check_public_https_url", lambda u: u)
    r = await api.post(url, json={"url": "https://cdn.example.com/match/final.mp4?sig=1"})
    assert r.status_code == 202
    assert r.json()["filename"] == "final.mp4"
    _queue, func, job_id, kwargs = api.app.state.jobs.jobs[-1]
    assert func == "handball_worker.ingest.run_import"
    assert kwargs["url"].startswith("https://cdn.example.com/")
    # when the import succeeds, ingest starts automatically
    token = {"x-internal-token": api.app.state.settings.internal_token.get_secret_value()}
    await api.http.post(
        f"/internal/jobs/{job_id}",
        headers=token,
        json={"status": "succeeded", "progress": 1, "result": {"size_bytes": 12345}},
    )
    assert api.app.state.jobs.jobs[-1][1] == "handball_worker.ingest.run_ingest"
    match = (await api.get(f"/v1/orgs/{ids['org']}/matches/{m['id']}")).json()
    assert match["videos"][0]["size_bytes"] == 12345
    assert [j["kind"] for j in match["jobs"]] == ["ingest", "import"]


async def test_clips_playlists_comments_annotations(
    make_api: Callable[[], Api], outbox: MemoryEmailSender
) -> None:
    coach = make_api()
    ids = await setup_club(coach)
    org = ids["org"]
    m = await new_match(coach, ids)
    clip = (
        await coach.post(
            f"/v1/orgs/{org}/clips",
            json={"match_id": m["id"], "start_ms": 1000, "end_ms": 9000, "title": "Kreuzung"},
        )
    ).json()
    assert (
        await coach.post(
            f"/v1/orgs/{org}/clips", json={"match_id": m["id"], "start_ms": 5, "end_ms": 5}
        )
    ).status_code == 422
    assert len((await coach.get(f"/v1/orgs/{org}/matches/{m['id']}/clips")).json()) == 1
    pl = (
        await coach.post(f"/v1/orgs/{org}/teams/{ids['team']}/playlists", json={"title": "Abwehr"})
    ).json()
    base = f"/v1/orgs/{org}/playlists/{pl['id']}"
    await coach.post(f"{base}/items", json={"clip_id": clip["id"], "note": "Hier zu spät"})
    detail = (
        await coach.post(
            f"{base}/items",
            json={"clip": {"match_id": m["id"], "start_ms": 20000, "end_ms": 25000}},
        )
    ).json()
    assert [i["position"] for i in detail["items"]] == [1, 2]
    assert detail["items"][0]["match_label"].startswith("TV Gegner (07.11.2026")
    ids_rev = [i["id"] for i in reversed(detail["items"])]
    detail = (await coach.put(f"{base}/order", json={"item_ids": ids_rev})).json()
    assert [i["clip"]["start_ms"] for i in detail["items"]] == [20000, 1000]
    assert (await coach.put(f"{base}/order", json={"item_ids": ids_rev[:1]})).status_code == 422

    # a player sees only shared playlists, can comment, cannot draw or clip
    await coach.post(
        f"/v1/orgs/{org}/invitations",
        json={"email": "p@hc-test.ch", "team_id": ids["team"], "team_role": "player"},
    )
    token = re.search(r"/invite/([\w-]+)", outbox.outbox[-1].text).group(1)  # type: ignore[union-attr]
    player = make_api()
    await player.register("p@hc-test.ch", invitation_token=token)
    assert (await player.get(f"/v1/orgs/{org}/teams/{ids['team']}/playlists")).json() == []
    assert (await player.get(base)).status_code == 404
    await coach.patch(base, json={"shared_with_players": True})
    assert len((await player.get(f"/v1/orgs/{org}/teams/{ids['team']}/playlists")).json()) == 1
    assert (await player.get(base)).status_code == 200
    assert (
        await player.post(
            f"/v1/orgs/{org}/clips", json={"match_id": m["id"], "start_ms": 0, "end_ms": 10}
        )
    ).status_code == 403

    c = (
        await player.post(
            f"/v1/orgs/{org}/matches/{m['id']}/comments",
            json={"t_ms": 61000, "body": " Gute Abwehr "},
        )
    ).json()
    assert c["body"] == "Gute Abwehr"
    await coach.post(
        f"/v1/orgs/{org}/matches/{m['id']}/comments", json={"t_ms": 1000, "body": "Start"}
    )
    comments = (await player.get(f"/v1/orgs/{org}/matches/{m['id']}/comments")).json()
    assert [x["t_ms"] for x in comments] == [1000, 61000]
    assert [x["can_delete"] for x in comments] == [False, True]
    coach_comment = comments[0]["id"]
    assert (await player.delete(f"/v1/orgs/{org}/comments/{coach_comment}")).status_code == 403
    assert (await coach.delete(f"/v1/orgs/{org}/comments/{c['id']}")).status_code == 204

    shape = {"kind": "arrow", "points": [[0.1, 0.2], [0.5, 0.5]], "color": "#ff0000"}
    a = await coach.post(
        f"/v1/orgs/{org}/matches/{m['id']}/annotations", json={"t_ms": 5000, "shapes": [shape]}
    )
    assert a.status_code == 201
    bad = await coach.post(
        f"/v1/orgs/{org}/matches/{m['id']}/annotations",
        json={"t_ms": 5000, "shapes": [{**shape, "points": [[1.5, 0]]}]},
    )
    assert bad.status_code == 422
    assert (
        await player.post(
            f"/v1/orgs/{org}/matches/{m['id']}/annotations", json={"t_ms": 1, "shapes": [shape]}
        )
    ).status_code == 403
    assert len((await player.get(f"/v1/orgs/{org}/matches/{m['id']}/annotations")).json()) == 1
    assert (await coach.delete(f"/v1/orgs/{org}/annotations/{a.json()['id']}")).status_code == 204

    assert (await coach.delete(f"{base}/items/{detail['items'][0]['id']}")).status_code == 204
    assert (await coach.delete(f"/v1/orgs/{org}/clips/{clip['id']}")).status_code == 204
    assert (await coach.delete(base)).status_code == 204

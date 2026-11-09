"""Push tokens and push jobs for the native apps (addendum 01, 5.5)."""

from __future__ import annotations

import uuid
from collections.abc import Callable

import asyncpg
import pytest

from handball_api.core.db import enable_system_access, open_session
from handball_api.core.jobs import MemoryJobQueue
from handball_api.services import training
from handball_api.services.context import Ctx

from .conftest import Api, setup_club

pytestmark = pytest.mark.usefixtures("clean_db")


async def test_devices_and_push_jobs(
    make_api: Callable[[], Api], owner_conn: asyncpg.Connection
) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    assert (
        await api.post("/v1/me/devices", json={"token": "nope-token-x", "platform": "ios"})
    ).status_code == 422
    token = "ExponentPushToken[abc123]"
    assert (
        await api.post("/v1/me/devices", json={"token": token, "platform": "ios"})
    ).status_code == 204
    assert (
        await api.post("/v1/me/devices", json={"token": token, "platform": "ios"})
    ).status_code == 204
    assert await owner_conn.fetchval("SELECT count(*) FROM device_tokens") == 1

    # an assignment to the coach (as a player account) notifies and queues a push
    jobs: MemoryJobQueue = api.app.state.jobs
    before = len(jobs.jobs)
    user_id = await owner_conn.fetchval("SELECT id FROM users LIMIT 1")

    async with open_session() as db:
        ctx = Ctx(
            db=db,
            settings=api.app.state.settings,
            email=api.app.state.email,
            storage=api.app.state.storage,
            jobs=jobs,
        )
        await enable_system_access(db, reason="test")
        await training.notify(
            ctx, __import__("uuid").UUID(org), [user_id], "assignment", {}, f"/app/{org}"
        )
        await db.commit()
    push_jobs = [j for j in jobs.jobs[before:] if j[1] == "handball_worker.push.send"]
    assert len(push_jobs) == 1
    payload = push_jobs[0][3]["payload"]
    assert payload["tokens"] == [token] and payload["body"] == "Neue Aufgabe vom Trainerteam"
    assert payload["data"] == {"kind": "assignment", "link": f"/app/{org}"}

    # signing out on the phone removes the token
    assert (await api.delete(f"/v1/me/devices/{token}")).status_code == 204
    assert await owner_conn.fetchval("SELECT count(*) FROM device_tokens") == 0


async def test_native_login_with_bearer_token(make_api: Callable[[], Api]) -> None:
    api = make_api()
    await setup_club(api)
    native = make_api()
    r = await native.http.post(
        "/v1/auth/login",
        json={"email": "coach@hc-test.ch", "password": "correct-horse-1"},
        headers={"x-client": "native"},
    )
    assert r.status_code == 200, r.text
    token = r.json()["token"]
    assert token and "set-cookie" not in r.headers
    bearer = {"authorization": f"Bearer {token}"}
    me = await native.http.get("/v1/me", headers=bearer)
    assert me.status_code == 200 and me.json()["email"] == "coach@hc-test.ch"
    # unsafe requests work without CSRF token (no cookie involved)
    ok = await native.http.post(
        "/v1/me/devices",
        json={"token": "ExponentPushToken[n1]", "platform": "android"},
        headers=bearer,
    )
    assert ok.status_code == 204
    assert (
        await native.http.get("/v1/me", headers={"authorization": "Bearer wrong"})
    ).status_code == 401
    # a browser login never gets the token in the body
    web = await make_api().http.post(
        "/v1/auth/login", json={"email": "coach@hc-test.ch", "password": "correct-horse-1"}
    )
    assert web.json().get("token") is None


async def test_signed_media_for_the_app(
    make_api: Callable[[], Api], owner_conn: asyncpg.Connection
) -> None:
    from handball_api.core.storage import MemoryStorage
    from handball_api.models import VideoAsset
    from handball_api.services.videos import media_prefix

    from .test_matches import new_match, upload

    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    m = await new_match(api, ids)
    vid = (await upload(api, ids, m["id"], b"v" * 100))["id"]
    async with open_session() as db:
        await enable_system_access(db, reason="test")
        asset = await db.get(VideoAsset, uuid.UUID(vid))
        assert asset is not None
        prefix = media_prefix(asset)
    storage: MemoryStorage = api.app.state.storage
    bucket = api.app.state.settings.s3_bucket_videos
    await storage.put(
        bucket, prefix + "hls/master.m3u8", b"#EXTM3U\nseg0.ts\n", "application/vnd.apple.mpegurl"
    )
    await storage.put(bucket, prefix + "hls/seg0.ts", b"TS", "video/mp2t")

    signed = (await api.post(f"/v1/orgs/{org}/videos/{vid}/media-token")).json()
    anon = make_api()  # the native player sends no cookie and no header
    playlist = await anon.get(signed["base"] + "hls/master.m3u8")
    assert playlist.status_code == 200 and playlist.content.startswith(b"#EXTM3U")
    # relative segment URLs resolve inside the same signed path
    assert (await anon.get(signed["base"] + "hls/seg0.ts")).content == b"TS"
    forged = signed["base"].replace(signed["base"].split("/")[-2], "9999999999.deadbeef")
    assert (await anon.get(forged + "hls/master.m3u8")).status_code == 404
    expired = f"/v1/media/{vid}/1.abc/hls/master.m3u8"
    assert (await anon.get(expired)).status_code == 404
    assert (await anon.get(signed["base"] + "proxy.mp4")).status_code == 404
    # someone from another club gets no token
    other = make_api()
    await setup_club(other, email="other@hc-test.ch")
    assert (await other.post(f"/v1/orgs/{org}/videos/{vid}/media-token")).status_code in (403, 404)

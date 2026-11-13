"""Courtside marks with device time and automatic sync (addendum 01, 5.3)."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import asyncpg
import pytest

from .conftest import Api, setup_club
from .test_matches import new_match, upload

pytestmark = pytest.mark.usefixtures("clean_db")

RECORDED = datetime(2026, 11, 7, 17, 58, 0, tzinfo=UTC)  # camera clock: video starts here
CAMERA_ERROR = timedelta(seconds=40)  # the camera clock is 40 s behind the phones


async def test_marks_upload_sync_and_list(
    make_api: Callable[[], Api], owner_conn: asyncpg.Connection
) -> None:
    api = make_api()
    ids = await setup_club(api)
    org, team = ids["org"], ids["team"]

    # buttons: defaults, then a custom set of four
    keys = (await api.get(f"/v1/orgs/{org}/teams/{team}/mark-keys")).json()
    assert [k["key"] for k in keys][:2] == ["goal_own", "goal_opp"]
    custom = [
        {"key": "goal_own", "label": "Tor"},
        {"key": "goal_opp", "label": "Gegentor"},
        {"key": "press", "label": "Pressing", "color": "#123456"},
        {"key": "look", "label": "Anschauen"},
    ]
    r = await api.put(f"/v1/orgs/{org}/teams/{team}/mark-keys", json={"keys": custom})
    assert r.status_code == 200 and r.json()[2]["label"] == "Pressing"
    bad = await api.put(f"/v1/orgs/{org}/teams/{team}/mark-keys", json={"keys": custom[:3]})
    assert bad.status_code == 422
    dup = [*custom[:3], {"key": "halftime"}]
    assert (
        await api.put(f"/v1/orgs/{org}/teams/{team}/mark-keys", json={"keys": dup})
    ).status_code == 422

    m = await new_match(api, ids)
    session = (
        await api.post(f"/v1/orgs/{org}/matches/{m['id']}/mark-sessions", json={"device": "iPhone"})
    ).json()
    assert session["offset_ms"] is None
    # the phone's real time of the video start is RECORDED + CAMERA_ERROR; goals in the video:
    goals_ms = [180_000, 610_000, 1_400_000, 2_100_000, 3_000_000]
    phone_start = RECORDED + CAMERA_ERROR
    marks = [
        {
            "client_id": str(uuid.uuid4()),
            "device_time": (phone_start + timedelta(milliseconds=g + 2000)).isoformat(),
            "key": "goal_own" if i % 2 == 0 else "goal_opp",
        }
        for i, g in enumerate(goals_ms)
    ]
    marks.append(
        {
            "client_id": str(uuid.uuid4()),
            "device_time": (phone_start + timedelta(milliseconds=1_800_000)).isoformat(),
            "key": "halftime",
        }
    )
    marks.append(
        {
            "client_id": str(uuid.uuid4()),
            "device_time": (phone_start + timedelta(milliseconds=2_500_000)).isoformat(),
            "key": "press",
            "note": "gut gelaufen",
        }
    )
    url = f"/v1/orgs/{org}/mark-sessions/{session['id']}/marks"
    first = await api.post(url, json={"marks": marks})
    assert first.status_code == 200 and len(first.json()["stored"]) == 7
    # the upload is retried after a lost response: nothing is stored twice
    again = await api.post(url, json={"marks": marks})
    assert [s["id"] for s in again.json()["stored"]] == [s["id"] for s in first.json()["stored"]]
    assert await owner_conn.fetchval("SELECT count(*) FROM live_tags") == 7

    listed = (await api.get(f"/v1/orgs/{org}/matches/{m['id']}/marks")).json()
    assert len(listed["marks"]) == 6 and all(x["t_ms"] is None for x in listed["marks"])

    # video with the camera's recording start and goals in it, then sync
    vid = (await upload(api, ids, m["id"], b"v" * 100))["id"]
    await owner_conn.execute(
        "UPDATE video_assets SET recorded_at = $1 WHERE id = $2::uuid", RECORDED, vid
    )
    for i, g in enumerate(goals_ms):
        r = await api.post(
            f"/v1/orgs/{org}/matches/{m['id']}/events",
            json={
                "type": "shot",
                "side": "own" if i % 2 == 0 else "opponent",
                "outcome": "goal",
                "t_ms": g,
            },
        )
        assert r.status_code == 201, r.text
    synced = (await api.post(f"/v1/orgs/{org}/matches/{m['id']}/marks/sync")).json()
    assert synced[0]["source"] == "events" and synced[0]["matched"] == 5
    expected_offset = -round(phone_start.timestamp() * 1000)
    assert abs(synced[0]["offset_ms"] - expected_offset) <= 100
    listed = (await api.get(f"/v1/orgs/{org}/matches/{m['id']}/marks")).json()
    by_key = {x["key"]: x for x in listed["marks"]}
    assert abs(by_key["press"]["t_ms"] - 2_500_000) <= 100 and by_key["press"]["half"] == 2
    assert by_key["press"]["label"] == "Pressing" and by_key["press"]["note"] == "gut gelaufen"
    assert sorted(x["half"] for x in listed["marks"]) == [1, 1, 1, 2, 2, 2]

    # a manual correction wins over later syncs
    r = await api.put(
        f"/v1/orgs/{org}/mark-sessions/{session['id']}/offset",
        json={"offset_ms": expected_offset + 1000},
    )
    assert r.json()["sync_source"] == "manual"
    synced = (await api.post(f"/v1/orgs/{org}/matches/{m['id']}/marks/sync")).json()
    assert synced[0]["offset_ms"] == expected_offset + 1000

    # without goals the camera clock is the fallback (with its error)
    await owner_conn.execute("DELETE FROM events")
    await owner_conn.execute("UPDATE live_tag_sessions SET sync_source = NULL")
    synced = (await api.post(f"/v1/orgs/{org}/matches/{m['id']}/marks/sync")).json()
    assert synced[0]["source"] == "metadata"
    assert synced[0]["offset_ms"] == -round(RECORDED.timestamp() * 1000)


async def test_a_mark_uploaded_twice_is_stored_once_per_match(
    make_api: Callable[[], Api], owner_conn: asyncpg.Connection
) -> None:
    """UX test N02: an offline mark sent again, also from a second session that a race opened on
    the same phone, is stored once; the list carries the phone's id to merge with the queue."""
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    m = await new_match(api, ids)
    url = f"/v1/orgs/{org}/matches/{m['id']}/mark-sessions"
    a = (await api.post(url, json={"device": "Phone"})).json()
    b = (await api.post(url, json={"device": "Phone"})).json()
    mark = {"client_id": str(uuid.uuid4()), "device_time": RECORDED.isoformat(), "key": "good"}
    first = await api.post(f"/v1/orgs/{org}/mark-sessions/{a['id']}/marks", json={"marks": [mark]})
    second = await api.post(f"/v1/orgs/{org}/mark-sessions/{b['id']}/marks", json={"marks": [mark]})
    assert first.json()["stored"][0]["id"] == second.json()["stored"][0]["id"]
    assert await owner_conn.fetchval("SELECT count(*) FROM live_tags") == 1
    listed = (await api.get(f"/v1/orgs/{org}/matches/{m['id']}/marks")).json()["marks"]
    assert [x["client_id"] for x in listed] == [mark["client_id"]]


async def test_the_last_mark_can_be_taken_back(
    make_api: Callable[[], Api], owner_conn: asyncpg.Connection
) -> None:
    """UX test N14: «Zurücknehmen» removes a mark by the phone's id; a second call is harmless."""
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    m = await new_match(api, ids)
    s = (await api.post(f"/v1/orgs/{org}/matches/{m['id']}/mark-sessions", json={})).json()
    mark = {"client_id": str(uuid.uuid4()), "device_time": RECORDED.isoformat(), "key": "two_min"}
    await api.post(f"/v1/orgs/{org}/mark-sessions/{s['id']}/marks", json={"marks": [mark]})
    url = f"/v1/orgs/{org}/matches/{m['id']}/marks/{mark['client_id']}"
    assert (await api.delete(url)).status_code == 204
    assert (await api.delete(url)).status_code == 204
    assert await owner_conn.fetchval("SELECT count(*) FROM live_tags") == 0

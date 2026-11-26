"""The export payload of a clip slide with a spotlight: tracks and the latest court of its video
(services/presentations.start_export reads the videos and calibrations in one query each)."""

from __future__ import annotations

import json
from collections.abc import Callable

import asyncpg
import pytest

from .conftest import Api, setup_club
from .test_matches import new_match, upload

pytestmark = pytest.mark.usefixtures("clean_db")


async def test_spotlight_export_carries_the_latest_court(
    make_api: Callable[[], Api], owner_conn: asyncpg.Connection
) -> None:
    coach = make_api()
    ids = await setup_club(coach)
    o = f"/v1/orgs/{ids['org']}"
    m = await new_match(coach, ids)
    video = await upload(coach, ids, m["id"], b"v" * 100)
    await owner_conn.execute(
        "UPDATE video_assets SET proxy_key = 'x/proxy.mp4', analysis = $1::jsonb "
        "WHERE id = $2::uuid",
        json.dumps({"chunk_ms": 10_000}),
        video["id"],
    )
    for age, h in ((2, 1.0), (1, 2.0)):
        await owner_conn.execute(
            "INSERT INTO calibrations (id, organization_id, video_asset_id, homography, "
            "image_size, confidence, reprojection_px, source, pipeline_version, created_at) "
            "SELECT gen_random_uuid(), organization_id, id, $1::jsonb, '[1280, 720]', 0.9, 1.0, "
            "'auto', '0.2.0', now() - $2::int * interval '1 hour' "
            "FROM video_assets WHERE id = $3::uuid",
            json.dumps([[h, 0, 0], [0, 1, 0], [0, 0, 1]]),
            age,
            video["id"],
        )
    pres = (
        await coach.post(
            f"{o}/teams/{ids['team']}/presentations", json={"title": "T", "match_id": m["id"]}
        )
    ).json()
    base = f"{o}/presentations/{pres['id']}"
    for spotlight in ([7], None):
        content = {"video_id": video["id"], "in_ms": 1000, "out_ms": 5000}
        if spotlight:
            content["spotlight"] = spotlight
        r = await coach.post(f"{base}/slides", json={"type": "clip", "content": content})
        assert r.status_code == 201, r.text
    assert (await coach.post(f"{base}/export")).status_code == 202
    payload = coach.app.state.jobs.jobs[-1][3]["payload"]
    assert payload["sources"] == {video["id"]: "x/proxy.mp4"}
    info = payload["analysis"][video["id"]]
    assert info["chunk_ms"] == 10_000 and info["chunks_prefix"].endswith("/analysis/")
    assert info["homography"][0][0] == 2.0  # the newer court
    # a moving camera: its court refers to the hall image, the export draws no spotlight
    await owner_conn.execute(
        "UPDATE video_assets SET analysis = $1::jsonb WHERE id = $2::uuid",
        json.dumps({"chunk_ms": 10_000, "camera": "moving", "view_chunks": 1}),
        video["id"],
    )
    assert (await coach.post(f"{base}/export")).status_code == 202
    payload = coach.app.state.jobs.jobs[-1][3]["payload"]
    assert video["id"] not in payload["analysis"]

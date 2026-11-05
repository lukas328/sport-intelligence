"""Presentation mode (addendum 01, 4.1)."""

from __future__ import annotations

import io
import re
from collections.abc import Callable

import asyncpg
import pytest
from PIL import Image

from handball_api.core.email import MemoryEmailSender

from .conftest import Api, setup_club
from .test_matches import new_match, upload
from .test_tactics import doc

pytestmark = pytest.mark.usefixtures("clean_db")
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


async def test_presentation_flow(
    make_api: Callable[[], Api], outbox: MemoryEmailSender, owner_conn: asyncpg.Connection
) -> None:
    coach = make_api()
    ids = await setup_club(coach)
    org, team = ids["org"], ids["team"]
    o = f"/v1/orgs/{org}"
    m = await new_match(coach, ids)
    video = await upload(coach, ids, m["id"], b"v" * 100)
    play = (
        await coach.post(
            f"{o}/teams/{team}/plays", json={"name": "Kreuzen", "category": "attack", "doc": doc()}
        )
    ).json()
    clip = (
        await coach.post(
            f"{o}/clips", json={"match_id": m["id"], "start_ms": 10_000, "end_ms": 18_000}
        )
    ).json()

    r = await coach.post(
        f"{o}/teams/{team}/presentations",
        json={"title": "Video-Sitzung Dienstag", "match_id": m["id"]},
    )
    assert r.status_code == 201, r.text
    pres = r.json()
    base = f"{o}/presentations/{pres['id']}"
    slides = [
        {
            "type": "text",
            "content": {
                "title": "Rückzug",
                "body": "Was fällt auf?",
                "notes": "Frage an die Aussen",
            },
        },
        {
            "type": "clip",
            "clip_id": clip["id"],
            "content": {
                "holds": [{"t_ms": 12_000, "duration_ms": 3000, "shapes": []}],
                "notes": "Hier fehlt der Rückzug",
            },
        },
        {
            "type": "clip",
            "content": {
                "video_id": video["id"],
                "in_ms": 30_000,
                "out_ms": 36_000,
                "slow": [{"from_ms": 31_000, "to_ms": 33_000, "rate": 0.5}],
            },
        },
        {"type": "tactics_board", "play_id": play["id"], "content": {}},
        {
            "type": "stat_card",
            "content": {
                "title": "Abschluss",
                "rows": [{"label": "Wurfquote", "value": "52 %", "n": 31}],
            },
        },
        {"type": "image", "content": {"caption": "Hallenplan"}},
    ]
    created = []
    for s in slides:
        res = await coach.post(f"{base}/slides", json=s)
        assert res.status_code == 201, res.text
        created.append(res.json())
    assert (
        created[1]["content"]["in_ms"] == 10_000
        and created[1]["content"]["video_id"] == video["id"]
    )
    bad = await coach.post(
        f"{base}/slides",
        json={"type": "clip", "content": {"video_id": video["id"], "in_ms": 5000, "out_ms": 1000}},
    )
    assert bad.status_code == 422

    order = [c["id"] for c in reversed(created)]
    det = (await coach.put(f"{base}/order", json={"slide_ids": order})).json()
    assert [s["id"] for s in det["slide_list"]] == order and det["can_edit"] is True
    assert (await coach.put(f"{base}/order", json={"slide_ids": order[:2]})).status_code == 422

    img = io.BytesIO()
    Image.new("RGB", (40, 20), (200, 0, 0)).save(img, "PNG")
    up = await coach.put(
        f"{o}/slides/{created[5]['id']}/image",
        files={"file": ("p.png", img.getvalue(), "image/png")},
    )
    assert up.status_code == 204
    assert (await coach.get(f"{o}/slides/{created[5]['id']}/image")).content.startswith(b"\x89PNG")
    assert (
        await coach.put(
            f"{o}/slides/{created[0]['id']}/image", files={"file": ("p.png", PNG, "image/png")}
        )
    ).status_code == 422

    await coach.patch(
        f"{o}/slides/{created[0]['id']}", json={"content": {"title": "Rückzug (neu)"}}
    )
    assert (await coach.delete(f"{o}/slides/{created[3]['id']}")).status_code == 204
    det = (await coach.get(base)).json()
    assert det["slides"] == 5 and [s["position"] for s in det["slide_list"]] == [0, 1, 2, 3, 4]

    # players see shared presentations only, read-only
    await coach.post(
        f"{o}/invitations", json={"email": "p@hc-test.ch", "team_id": team, "team_role": "player"}
    )
    token = re.search(r"/invite/([\w-]+)", outbox.outbox[-1].text)
    assert token
    player = make_api()
    await player.register("p@hc-test.ch", invitation_token=token.group(1))
    assert (await player.get(f"{o}/teams/{team}/presentations")).json() == []
    assert (await player.get(base)).status_code == 404
    await coach.patch(base, json={"shared_with_players": True})
    assert [p["id"] for p in (await player.get(f"{o}/teams/{team}/presentations")).json()] == [
        pres["id"]
    ]
    seen = (await player.get(base)).json()
    assert seen["can_edit"] is False
    assert (
        await player.post(f"{base}/slides", json={"type": "text", "content": {}})
    ).status_code == 403

    # phone remote: pairing key, commands reach the presenter's channel
    pair = (await coach.post(f"{base}/remote")).json()
    assert len(pair["key"]) >= 16
    cmd = await coach.post(f"{base}/remote/command", json={"key": pair["key"], "action": "next"})
    assert cmd.status_code == 204
    published = coach.app.state.events.published
    assert published[-1][0] == f"presentation:{pres['id']}:{pair['key']}"
    assert published[-1][1]["action"] == "next"
    assert (
        await player.post(f"{base}/remote/command", json={"key": pair["key"], "action": "next"})
    ).status_code == 403

    # MP4 export via worker, callback, download
    await owner_conn.execute(
        "UPDATE video_assets SET proxy_key = $1 WHERE id = $2::uuid", "x/proxy.mp4", video["id"]
    )
    ex = await coach.post(f"{base}/export")
    assert ex.status_code == 202 and ex.json()["export_status"] == "queued"
    queue, func, _, kwargs = coach.app.state.jobs.jobs[-1]
    assert (queue, func) == ("default", "handball_worker.export.run_presentation_export")
    payload = kwargs["payload"]
    assert payload["sources"] == {video["id"]: "x/proxy.mp4"}
    assert [s["type"] for s in payload["slides"]] == ["stat_card", "clip", "clip", "text"]
    assert payload["slides"][0]["lines"] == ["Abschluss", "Wurfquote: 52 % (n = 31)"]
    internal = {"x-internal-token": coach.app.state.settings.internal_token.get_secret_value()}
    await coach.app.state.storage.put(
        coach.app.state.settings.s3_bucket_artifacts, payload["out_key"], b"mp4", "video/mp4"
    )
    done = await coach.post(
        f"/internal/presentations/{pres['id']}/export",
        json={"status": "ready", "key": payload["out_key"]},
        headers=internal,
    )
    assert done.status_code == 204
    assert (await coach.get(f"{base}/export.mp4")).content == b"mp4"

    # PDF with stills from the thumbnail sprite
    storage = coach.app.state.storage
    prefix = f"{org}/{m['id']}/{video['id']}/"
    sprite = io.BytesIO()
    Image.new("RGB", (320, 90), (0, 90, 200)).save(sprite, "JPEG")
    await storage.put(
        coach.app.state.settings.s3_bucket_videos,
        prefix + "thumbs.jpg",
        sprite.getvalue(),
        "image/jpeg",
    )
    vtt = (
        "WEBVTT\n\n00:00:00.000 --> 00:00:20.000\nthumbs.jpg#xywh=0,0,160,90\n\n"
        "00:00:20.000 --> 00:00:40.000\nthumbs.jpg#xywh=160,0,160,90\n"
    )
    await storage.put(
        coach.app.state.settings.s3_bucket_videos, prefix + "thumbs.vtt", vtt.encode(), "text/vtt"
    )
    pdf = await coach.get(f"{base}/pdf", params={"lang": "fr"})
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    assert pdf.content.count(b"/Subtype /Image") >= 2
    assert (await coach.delete(base)).status_code == 204


async def test_presentation_from_scouting(make_api: Callable[[], Api]) -> None:
    from .test_scouting import _earlier_match

    coach = make_api()
    ids = await setup_club(coach)
    await _earlier_match(coach, ids, "2026-09-05T18:00:00+02:00")
    upcoming = await new_match(
        coach, ids, opponent_name="TV Gegner", kickoff_at="2026-12-05T18:00:00+01:00"
    )
    rep = (await coach.post(f"/v1/orgs/{ids['org']}/matches/{upcoming['id']}/scouting")).json()
    r = await coach.post(f"/v1/orgs/{ids['org']}/scouting/{rep['id']}/presentation")
    assert r.status_code == 201
    det = r.json()
    assert det["title"].startswith("TV Gegner")
    assert det["slide_list"][0]["type"] == "stat_card"
    assert any(s["type"] == "text" and "observation" in s["content"] for s in det["slide_list"])


async def test_clip_slide_needs_a_video(make_api: Callable[[], Api]) -> None:
    """A clip of a match without video (e.g. from a Sportscode import before the upload) or a
    broken video id used to fail with a server error; a clip of another team is not found."""
    coach = make_api()
    ids = await setup_club(coach)
    org, team = ids["org"], ids["team"]
    o = f"/v1/orgs/{org}"
    m = await new_match(coach, ids)
    clip = (
        await coach.post(f"{o}/clips", json={"match_id": m["id"], "start_ms": 1000, "end_ms": 8000})
    ).json()
    pres = (
        await coach.post(f"{o}/teams/{team}/presentations", json={"title": "T", "match_id": m["id"]})
    ).json()
    slides = f"{o}/presentations/{pres['id']}/slides"
    r = await coach.post(slides, json={"type": "clip", "clip_id": clip["id"], "content": {}})
    assert r.status_code == 422 and r.json()["type"].endswith(":no-video"), r.text
    broken = {"type": "clip", "content": {"video_id": "nope", "in_ms": 0, "out_ms": 5}}
    assert (await coach.post(slides, json=broken)).status_code == 404
    # with a video the same clip works and plays the match's video
    video = await upload(coach, ids, m["id"], b"v" * 100)
    r = await coach.post(slides, json={"type": "clip", "clip_id": clip["id"], "content": {}})
    assert r.status_code == 201, r.text
    assert r.json()["content"]["video_id"] == video["id"]
    # a clip of another team of the club
    other = (
        await coach.post(f"{o}/teams", json={"name": "Damen 1", "gender": "women"})
    ).json()
    m2 = await new_match(coach, {**ids, "team": other["id"]})
    await upload(coach, ids, m2["id"], b"v" * 100)
    foreign = (
        await coach.post(f"{o}/clips", json={"match_id": m2["id"], "start_ms": 0, "end_ms": 5000})
    ).json()
    r = await coach.post(slides, json={"type": "clip", "clip_id": foreign["id"], "content": {}})
    assert r.status_code == 404, r.text

"""Share links (M8)."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from handball_api.core.storage import MemoryStorage

from .conftest import Api, setup_club
from .test_matches import new_match, upload
from .test_tactics import doc

pytestmark = pytest.mark.usefixtures("clean_db")


async def test_share_links(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    org, team = ids["org"], ids["team"]
    base = f"/v1/orgs/{org}/teams/{team}/share-links"
    play = (
        await api.post(
            f"/v1/orgs/{org}/teams/{team}/plays",
            json={"name": "Kreuzen", "category": "attack", "doc": doc()},
        )
    ).json()
    m = await new_match(api, ids)
    await api.post(
        f"/v1/orgs/{org}/matches/{m['id']}/events",
        json={"type": "shot", "side": "own", "outcome": "goal", "clock_s": 10, "number": 7},
    )
    vid = (await upload(api, ids, m["id"], b"v" * 100))["id"]
    other = await new_match(api, ids, opponent_name="Andere")
    other_vid = (await upload(api, ids, other["id"], b"w" * 100))["id"]
    pl = (
        await api.post(f"/v1/orgs/{org}/teams/{team}/playlists", json={"title": "Best of"})
    ).json()
    clip = {"match_id": m["id"], "start_ms": 1000, "end_ms": 5000, "title": "Tor"}
    await api.post(f"/v1/orgs/{org}/playlists/{pl['id']}/items", json={"clip": clip})

    links = {}
    for kind, target in (("play", play["id"]), ("match", m["id"]), ("playlist", pl["id"])):
        r = await api.post(base, json={"kind": kind, "target_id": target, "days": 7})
        assert r.status_code == 201, r.text
        links[kind] = r.json()
    assert len(links["play"]["token"]) > 20
    assert (await api.post(base, json={"kind": "play", "target_id": m["id"]})).status_code == 404

    anon = make_api()
    p = (await anon.get(f"/v1/share/{links['play']['token']}")).json()
    assert p["kind"] == "play" and p["play"]["name"] == "Kreuzen" and p["team"] == "Herren 1"
    mm = (await anon.get(f"/v1/share/{links['match']['token']}")).json()
    assert mm["match"]["own"]["goals"] == 1
    assert mm["match"]["players"][0]["number"] == 7
    assert "name" not in str(mm["match"]["players"])
    pp = (await anon.get(f"/v1/share/{links['playlist']['token']}")).json()
    assert pp["playlist"]["clips"][0]["title"] == "Tor"
    assert (await anon.get("/v1/share/not-a-token")).status_code == 404

    # media: only videos behind the shared content
    storage: MemoryStorage = api.app.state.storage
    video = (await api.get(f"/v1/orgs/{org}/matches/{m['id']}")).json()["videos"][0]
    assert video["id"] == vid
    prefix = f"{org}/{m['id']}/{vid}/"
    await storage.put(
        "videos", prefix + "hls/master.m3u8", b"#EXTM3U", "application/vnd.apple.mpegurl"
    )
    tok = links["playlist"]["token"]
    r = await anon.get(f"/v1/share/{tok}/videos/{vid}/media/hls/master.m3u8")
    assert r.status_code == 200 and r.content == b"#EXTM3U"
    assert (
        await anon.get(f"/v1/share/{tok}/videos/{other_vid}/media/hls/master.m3u8")
    ).status_code == 404
    assert (await anon.get(f"/v1/share/{tok}/videos/{vid}/media/proxy.mp4")).status_code == 404
    assert (
        await anon.get(f"/v1/share/{links['play']['token']}/videos/{vid}/media/hls/master.m3u8")
    ).status_code == 404

    listing = (await api.get(base)).json()
    assert {x["kind"]: x["views"] for x in listing} == {"play": 1, "match": 1, "playlist": 1}
    assert "token" not in listing[0]
    assert (
        await api.delete(f"/v1/orgs/{org}/share-links/{links['play']['id']}")
    ).status_code == 204
    assert (await anon.get(f"/v1/share/{links['play']['token']}")).status_code == 404

"""Share links (M8)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

import pytest

from handball_api.core.storage import MemoryStorage

from .conftest import Api, setup_club
from .test_matches import new_match, upload
from .test_tactics import doc
from .test_themes import ready_video

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


async def test_youth_teams_share_only_plays(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api, youth=True)
    org, team = ids["org"], ids["team"]
    base = f"/v1/orgs/{org}/teams/{team}/share-links"
    play = (
        await api.post(
            f"/v1/orgs/{org}/teams/{team}/plays",
            json={"name": "Kreuzen", "category": "attack", "doc": doc()},
        )
    ).json()
    m = await new_match(api, ids)
    pl = (await api.post(f"/v1/orgs/{org}/teams/{team}/playlists", json={"title": "U13"})).json()
    for kind, target in (("match", m["id"]), ("playlist", pl["id"])):
        r = await api.post(base, json={"kind": kind, "target_id": target, "days": 7})
        assert r.status_code == 403
        assert r.json()["type"].endswith("youth-protection")
    ok = await api.post(base, json={"kind": "play", "target_id": play["id"], "days": 7})
    assert ok.status_code == 201


async def test_share_scene_and_collection(make_api: Callable[[], Api]) -> None:
    """SPEC 7.8: one page for a scene, a collection or the highlights; 30 days by default,
    revocable, counted when opened, with Open Graph data that does not count."""
    api = make_api()
    ids = await setup_club(api)
    org, team = ids["org"], ids["team"]
    o = f"/v1/orgs/{org}"
    base = f"{o}/teams/{team}/share-links"
    m = await new_match(api, ids, opponent_name="TSV Thalwil")
    await ready_video(api, ids, m["id"])
    vid = (await api.get(f"{o}/matches/{m['id']}")).json()["videos"][0]["id"]
    other = await new_match(api, ids, opponent_name="Andere")
    other_vid = (await upload(api, ids, other["id"], b"w" * 100))["id"]
    clip = (
        await api.post(f"{o}/clips", json={"match_id": m["id"], "start_ms": 1000, "end_ms": 9000})
    ).json()
    coll = (
        await api.post(
            f"{o}/teams/{team}/collections",
            json={
                "title": "Rückzug",
                "items": [
                    {"kind": "note", "text": "Wer läuft zurück?"},
                    {"kind": "scene", "clip_id": clip["id"], "text": "Hier"},
                    {"kind": "scene", "match_id": m["id"], "start_ms": 20_000, "end_ms": 26_000},
                ],
            },
        )
    ).json()

    scene = await api.post(base, json={"kind": "scene", "target_id": clip["id"]})
    assert scene.status_code == 201, scene.text
    # 30 days unless said otherwise
    days = (scene.json()["expires_at"][:10], scene.json()["created_at"][:10])
    assert (date.fromisoformat(days[0]) - date.fromisoformat(days[1])).days == 30
    shared = await api.post(base, json={"kind": "collection", "target_id": coll["id"]})
    assert shared.status_code == 201, shared.text
    # another team's collection id is not shareable here
    bad = await api.post(base, json={"kind": "collection", "target_id": m["id"]})
    assert bad.status_code == 404

    anon = make_api()
    tok = shared.json()["token"]
    # the preview for the chat: title, club, length; no opening counted
    pv = (await anon.get(f"/v1/share/{tok}/preview")).json()
    assert (pv["title"], pv["club"], pv["team"], pv["scenes"], pv["duration_s"]) == (
        "Rückzug",
        "HC Test",
        "Herren 1",
        2,
        14,
    )
    assert pv["kit"] == {"a": "#112233", "b": "#ffffff", "pattern": "uni"}
    page = (await anon.get(f"/v1/share/{tok}")).json()
    assert page["kind"] == "collection" and page["collection"]["title"] == "Rückzug"
    assert [i["kind"] for i in page["collection"]["items"]] == ["note", "scene", "scene"]
    assert page["collection"]["items"][1]["scene"]["video_id"] == vid
    one = (await anon.get(f"/v1/share/{scene.json()['token']}")).json()
    assert one["scene"]["items"][0]["scene"]["start_ms"] == 1000

    # media only behind the shared scenes
    storage: MemoryStorage = api.app.state.storage
    await storage.put(
        "videos", f"{org}/{m['id']}/{vid}/hls/master.m3u8", b"#EXTM3U", "application/x-mpegurl"
    )
    assert (
        await anon.get(f"/v1/share/{tok}/videos/{vid}/media/hls/master.m3u8")
    ).status_code == 200
    assert (
        await anon.get(f"/v1/share/{tok}/videos/{other_vid}/media/hls/master.m3u8")
    ).status_code == 404

    # "n-mal geöffnet": the page counts, the preview does not; then the link is revoked
    listing = {x["kind"]: x for x in (await api.get(base)).json()}
    assert listing["collection"]["views"] == 1 and listing["scene"]["views"] == 1
    await api.delete(f"{o}/share-links/{listing['collection']['id']}")
    assert (await anon.get(f"/v1/share/{tok}")).status_code == 404
    assert (await anon.get(f"/v1/share/{tok}/preview")).status_code == 404

from __future__ import annotations

import uuid
from collections.abc import Callable

import asyncpg

from .conftest import Api, setup_club
from .test_matches import new_match
from .test_themes import ready_video


async def test_collection_of_scenes_plays_and_notes(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    org, team = ids["org"], ids["team"]
    o = f"/v1/orgs/{org}"
    m = await new_match(api, ids)
    event = (
        await api.post(
            f"{o}/matches/{m['id']}/events",
            json={"type": "shot", "side": "opponent", "outcome": "goal", "t_ms": 65_000},
        )
    ).json()
    play = (
        await api.post(
            f"{o}/teams/{team}/plays",
            json={
                "name": "Kreuzen",
                "category": "attack",
                "doc": {
                    "formatVersion": 1,
                    "court": "half",
                    "frames": [{"tokens": [], "duration_ms": 1000}],
                },
            },
        )
    ).json()
    r = await api.post(
        f"{o}/teams/{team}/collections",
        json={
            "title": "Rückzug",
            "items": [
                {"kind": "note", "text": "Wer läuft zurück?"},
                {"kind": "scene", "event_id": event["id"], "text": "Hier zu spät"},
                {"kind": "scene", "match_id": m["id"], "start_ms": 1000, "end_ms": 9000},
                {"kind": "play", "play_id": play["id"]},
            ],
        },
    )
    assert r.status_code == 201, r.text
    c = r.json()
    assert (c["source"], c["editable"], c["draft"]) == ("collection", True, False)
    assert [i["kind"] for i in c["items"]] == ["note", "scene", "scene", "play"]
    # a scene from an event is a window around its moment, as long as in Szenen (V6)
    assert (c["items"][1]["scene"]["start_ms"], c["items"][1]["scene"]["end_ms"]) == (
        59_000,
        68_000,
    )
    assert c["items"][1]["text"] == "Hier zu spät"
    assert c["items"][3]["play"]["name"] == "Kreuzen"
    # reorder and trim: the entries are replaced as a whole
    base = f"{o}/collections/{c['id']}"
    kept = [{"kind": "scene", "clip_id": c["items"][2]["scene"]["clip_id"]}]
    trimmed = (await api.patch(base, json={"title": "Rückzug kurz", "items": kept})).json()
    assert trimmed["title"] == "Rückzug kurz" and len(trimmed["items"]) == 1
    # invalid entries
    bad = await api.patch(base, json={"items": [{"kind": "note"}]})
    assert bad.status_code == 422
    other = await api.patch(base, json={"items": [{"kind": "scene", "start_ms": 1, "end_ms": 2}]})
    assert other.status_code == 422
    assert (await api.delete(base)).status_code == 204
    assert (await api.get(base)).status_code == 404


async def test_older_objects_read_as_collections(
    make_api: Callable[[], Api], owner_conn: asyncpg.Connection
) -> None:
    api = make_api()
    ids = await setup_club(api)
    org, team = ids["org"], ids["team"]
    o = f"/v1/orgs/{org}"
    m = await new_match(api, ids)
    await ready_video(api, ids, m["id"])  # a clip slide needs a video
    clip = (
        await api.post(
            f"{o}/clips", json={"match_id": m["id"], "start_ms": 1000, "end_ms": 9000, "title": "K"}
        )
    ).json()
    pl = (await api.post(f"{o}/teams/{team}/playlists", json={"title": "Abwehr"})).json()
    await api.post(f"{o}/playlists/{pl['id']}/items", json={"clip_id": clip["id"], "note": "Da!"})
    pres = (await api.post(f"{o}/teams/{team}/presentations", json={"title": "Sitzung"})).json()
    await api.post(
        f"{o}/presentations/{pres['id']}/slides",
        json={"type": "text", "content": {"title": "Rückzug", "body": "Was fällt auf?"}},
    )
    slide = await api.post(
        f"{o}/presentations/{pres['id']}/slides",
        json={"type": "clip", "clip_id": clip["id"], "content": {}},
    )
    assert slide.status_code == 201, slide.text
    # an assignment needs players with accounts to be created through the API: stored directly
    task_id = str(uuid.uuid4())
    await owner_conn.execute(
        "INSERT INTO assignments (id, organization_id, team_id, kind, target_id, title, note) "
        "VALUES ($1::uuid, $2::uuid, $3::uuid, 'playlist', $4, 'Anschauen', 'Bis Dienstag')",
        task_id,
        org,
        team,
        pl["id"],
    )

    listed = (await api.get(f"{o}/teams/{team}/collections")).json()
    assert {x["source"] for x in listed} == {"playlist", "presentation", "assignment"}
    assert {x["title"]: x["entries"] for x in listed} == {"Abwehr": 1, "Sitzung": 2, "Anschauen": 2}

    as_pl = (await api.get(f"{o}/collections/{pl['id']}")).json()
    assert (as_pl["source"], as_pl["editable"]) == ("playlist", False)
    assert (
        as_pl["items"][0]["text"] == "Da!" and as_pl["items"][0]["scene"]["clip_id"] == clip["id"]
    )
    as_pres = (await api.get(f"{o}/collections/{pres['id']}")).json()
    assert [i["kind"] for i in as_pres["items"]] == ["note", "scene"]
    assert as_pres["items"][0]["text"] == "Rückzug\nWas fällt auf?"
    as_task = (await api.get(f"{o}/collections/{task_id}")).json()
    assert [i["kind"] for i in as_task["items"]] == ["note", "scene"]
    # older objects are changed where they are
    r = await api.patch(f"{o}/collections/{pl['id']}", json={"title": "Neu"})
    assert r.status_code == 409 and r.json()["type"].endswith(":read-only-source")
    # the old objects are unchanged
    assert (await api.get(f"{o}/playlists/{pl['id']}")).json()["title"] == "Abwehr"


async def test_draft_from_the_three_things(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    org, team = ids["org"], ids["team"]
    o = f"/v1/orgs/{org}"
    m = await new_match(api, ids)
    for k in range(5):  # an opponent run of five goals is one of the things
        await api.post(
            f"{o}/matches/{m['id']}/events",
            json={
                "type": "shot",
                "side": "opponent",
                "outcome": "goal",
                "t_ms": 20_000 * (k + 1),
                "clock_s": 60.0 * (k + 1),
            },
        )
    r = await api.post(
        f"{o}/teams/{team}/collections/from-match",
        json={"match_id": m["id"], "title": "Gegen TV Gegner"},
    )
    assert r.status_code == 201, r.text
    draft = r.json()
    assert draft["draft"] is True and draft["match_id"] == m["id"]
    assert draft["items"] and all(i["kind"] == "scene" for i in draft["items"])
    assert len(draft["items"]) <= 12

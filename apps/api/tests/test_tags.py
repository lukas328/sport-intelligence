"""Own tags, combined search and smart playlists (addendum 01, 4.4)."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from .conftest import Api, setup_club
from .test_matches import new_match
from .test_tactics import doc

pytestmark = pytest.mark.usefixtures("clean_db")


async def test_tags_search_and_smart_playlist(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    org, team = ids["org"], ids["team"]
    t = f"/v1/orgs/{org}"
    ts = await api.post(
        f"{t}/teams/{team}/tag-sets",
        json={
            "name": "Abwehr",
            "tags": [
                {"name": "Rückzug zu langsam", "color": "#dc2626", "hotkey": "r"},
                {"name": "Gute Abwehrarbeit"},
            ],
        },
    )
    assert ts.status_code == 201, ts.text
    slow, good = (
        x["id"] for x in sorted(ts.json()["tags"], key=lambda x: x["name"] != "Rückzug zu langsam")
    )
    assert (
        await api.post(f"{t}/teams/{team}/tag-sets", json={"name": "Abwehr"})
    ).status_code == 409

    m1 = await new_match(api, ids)
    m2 = await new_match(
        api, ids, opponent_name="HC Andere", kickoff_at="2026-11-14T18:00:00+01:00"
    )
    ev = f"{t}/matches/{m1['id']}/events"
    goal_against = (
        await api.post(
            ev, json={"type": "shot", "side": "opponent", "outcome": "goal", "t_ms": 60_000}
        )
    ).json()
    own_goal = (
        await api.post(ev, json={"type": "shot", "side": "own", "outcome": "goal", "t_ms": 90_000})
    ).json()
    other = (
        await api.post(
            f"{t}/matches/{m2['id']}/events",
            json={"type": "shot", "side": "opponent", "outcome": "goal", "t_ms": 3_000},
        )
    ).json()
    clip = (
        await api.post(
            f"{t}/clips", json={"match_id": m1["id"], "start_ms": 100_000, "end_ms": 110_000}
        )
    ).json()
    play = (
        await api.post(
            f"{t}/teams/{team}/plays", json={"name": "Kreuzen", "category": "attack", "doc": doc()}
        )
    ).json()

    links = f"{t}/tag-links"
    for target_type, target, tags in (
        ("event", goal_against["id"], [slow]),
        ("event", other["id"], [slow, good]),
        ("clip", clip["id"], [good]),
        ("play", play["id"], [good]),
    ):
        r = await api.put(
            links, json={"target_type": target_type, "target_id": target, "tag_ids": tags}
        )
        assert r.status_code == 200, r.text
    # tags of another team are rejected
    other_team = (await api.post(f"{t}/teams", json={"name": "Damen", "gender": "women"})).json()
    foreign = (
        await api.post(
            f"{t}/teams/{other_team['id']}/tag-sets", json={"name": "X", "tags": [{"name": "y"}]}
        )
    ).json()
    bad = await api.put(
        links,
        json={
            "target_type": "event",
            "target_id": own_goal["id"],
            "tag_ids": [foreign["tags"][0]["id"]],
        },
    )
    assert bad.status_code == 422

    per_match = (await api.get(f"{t}/matches/{m1['id']}/tag-links")).json()
    assert per_match["events"] == {goal_against["id"]: [slow]}
    assert per_match["clips"] == {clip["id"]: [good]}

    search = f"{t}/teams/{team}/search"
    res = (await api.post(search, json={"tags_any": [slow]})).json()
    assert [h["id"] for h in res["hits"]] == [goal_against["id"], other["id"]]
    assert res["hits"][0]["start_ms"] == 54_000 and res["hits"][0]["end_ms"] == 63_000
    assert res["facets"]["tags"] == {slow: 2, good: 1}
    both = (await api.post(search, json={"tags_all": [slow, good]})).json()
    assert [h["id"] for h in both["hits"]] == [other["id"]]
    # automatic attributes combined with own tags; own tags never change the statistics
    combo = (
        await api.post(
            search, json={"sides": ["opponent"], "tags_any": [slow], "match_ids": [m1["id"]]}
        )
    ).json()
    assert combo["total"] == 1
    goods = (await api.post(search, json={"tags_any": [good]})).json()
    assert {h["kind"] for h in goods["hits"]} == {"event", "clip"}
    stats = (await api.get(f"{t}/matches/{m1['id']}/stats")).json()
    assert stats["own"]["goals"] == 1 and stats["opponent"]["goals"] == 1

    saved = await api.post(
        f"{t}/teams/{team}/saved-filters",
        json={"name": "Rückzug", "query": {"tags_any": [slow], "sides": ["opponent"]}},
    )
    assert saved.status_code == 201
    run = f"{t}/saved-filters/{saved.json()['id']}/results"
    assert (await api.get(run)).json()["total"] == 2
    # smart: a new tagged event appears without editing the playlist
    new = (
        await api.post(
            ev, json={"type": "shot", "side": "opponent", "outcome": "goal", "t_ms": 200_000}
        )
    ).json()
    await api.put(links, json={"target_type": "event", "target_id": new["id"], "tag_ids": [slow]})
    assert (await api.get(run)).json()["total"] == 3
    assert [f["name"] for f in (await api.get(f"{t}/teams/{team}/saved-filters")).json()] == [
        "Rückzug"
    ]

    # removing tags and the tag set
    await api.put(links, json={"target_type": "event", "target_id": new["id"], "tag_ids": []})
    assert (await api.get(run)).json()["total"] == 2
    tag = await api.patch(f"{t}/tags/{good}", json={"name": "Starke Abwehr"})
    assert tag.json()["name"] == "Starke Abwehr"
    assert (await api.delete(f"{t}/saved-filters/{saved.json()['id']}")).status_code == 204
    assert (await api.delete(f"{t}/tag-sets/{ts.json()['id']}")).status_code == 204
    assert (await api.get(f"{t}/teams/{team}/tag-sets")).json() == []
    assert (await api.get(f"{t}/matches/{m1['id']}/tag-links")).json() == {
        "clips": {},
        "events": {},
    }

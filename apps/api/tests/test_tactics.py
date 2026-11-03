"""Play library (M6)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from .conftest import Api, setup_club
from .test_matches import new_match

pytestmark = pytest.mark.usefixtures("clean_db")


def doc(frames: int = 2) -> dict[str, Any]:
    return {
        "formatVersion": 1,
        "court": "half",
        "frames": [
            {
                "tokens": [
                    {"id": "a", "side": "own", "label": "RM", "x": 29 + i, "y": 10},
                    {"id": "b", "side": "opp", "label": "1", "x": 33, "y": 10},
                ],
                "ball": {"x": 29 + i, "y": 10},
                "arrows": [{"kind": "run", "points": [[29, 10], [31, 12]]}],
                "note": "",
                "duration_ms": 1500,
            }
            for i in range(frames)
        ],
    }


async def test_play_crud_search_and_validation(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    org, team = ids["org"], ids["team"]
    base = f"/v1/orgs/{org}/teams/{team}/plays"
    m = await new_match(api, ids)
    r = await api.post(
        base,
        json={
            "name": "Kreuzen RM-RR",
            "category": "attack",
            "formation": "3-3",
            "tags": ["Kreuzen", " Rückraum ", "Kreuzen", ""],
            "doc": doc(),
            "source": {"match_id": m["id"], "t_ms": 61_000},
        },
    )
    assert r.status_code == 201, r.text
    play = r.json()
    assert play["tags"] == ["Kreuzen", "Rückraum"]
    assert play["source"] == {"match_id": m["id"], "t_ms": 61_000}
    assert len(play["doc"]["frames"]) == 2
    await api.post(
        base, json={"name": "6:0", "category": "defence", "formation": "6-0", "doc": doc(1)}
    )

    assert [p["name"] for p in (await api.get(base)).json()] == ["6:0", "Kreuzen RM-RR"]
    assert [p["name"] for p in (await api.get(base, params={"q": "rück"})).json()] == [
        "Kreuzen RM-RR"
    ]
    assert [p["name"] for p in (await api.get(base, params={"category": "defence"})).json()] == [
        "6:0"
    ]

    url = f"/v1/orgs/{org}/plays/{play['id']}"
    upd = await api.patch(url, json={"name": "Kreuzen", "doc": doc(3), "shared_with_players": True})
    assert upd.status_code == 200, upd.text
    assert (
        upd.json()["name"],
        len(upd.json()["doc"]["frames"]),
        upd.json()["shared_with_players"],
    ) == (
        "Kreuzen",
        3,
        True,
    )
    assert (await api.get(url)).json()["name"] == "Kreuzen"

    bad = doc(1)
    bad["frames"][0]["tokens"].append(dict(bad["frames"][0]["tokens"][0]))
    assert (
        await api.post(base, json={"name": "x", "category": "attack", "doc": bad})
    ).status_code == 422
    bad = doc(1)
    bad["frames"][0]["duration_ms"] = 10
    assert (
        await api.post(base, json={"name": "x", "category": "attack", "doc": bad})
    ).status_code == 422
    assert (
        await api.post(
            base, json={"name": "x", "category": "attack", "doc": {**doc(1), "formatVersion": 2}}
        )
    ).status_code == 422
    assert (
        await api.post(
            base,
            json={
                "name": "x",
                "category": "attack",
                "doc": doc(1),
                "source": {"match_id": "00000000-0000-0000-0000-000000000001", "t_ms": 0},
            },
        )
    ).status_code == 422

    assert (await api.delete(url)).status_code == 204
    assert (await api.get(url)).status_code == 404

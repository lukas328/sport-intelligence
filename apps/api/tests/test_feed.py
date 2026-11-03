"""Player feed "Deine Szenen" and self-assessment (addendum 01, 4.7)."""

from __future__ import annotations

import re
import uuid
from collections.abc import Callable
from typing import Any

import pytest

from handball_api.core.email import MemoryEmailSender
from handball_api.models import Event
from handball_api.services.feed import Scene, classify, select_scenes

from .conftest import Api, setup_club
from .test_matches import new_match

PID = uuid.uuid4()


def _ev(**kw: Any) -> Event:
    base: dict[str, Any] = {"id": uuid.uuid4(), "side": "own", "attributes": {}, "player_id": PID}
    return Event(**{**base, **kw})


def test_classify_player_part() -> None:
    assert classify(_ev(type="shot", outcome="goal"), PID) == ("goal", True, 3.0)
    assert classify(_ev(type="shot", outcome="miss"), PID)[:2] == ("shot_missed", False)  # type: ignore[index]
    assist = _ev(type="shot", outcome="goal", player_id=uuid.uuid4(), assist_player_id=PID)
    assert classify(assist, PID) == ("assist", True, 2.5)
    save = _ev(
        type="shot",
        side="opponent",
        outcome="save",
        player_id=None,
        attributes={"goalkeeper_id": str(PID)},
    )
    assert classify(save, PID) == ("save", True, 3.0)
    assert classify(_ev(type="turnover"), PID) == ("turnover", False, 2.0)
    assert classify(_ev(type="shot", outcome="goal", player_id=uuid.uuid4()), PID) is None


def _scene(reason: str, positive: bool, score: float) -> Scene:
    return Scene(_ev(type="shot"), reason, positive, score)


def test_selection_mixes_and_protects_youth() -> None:
    many_misses = [_scene("shot_missed", False, 5 - i * 0.1) for i in range(6)]
    goals = [_scene("goal", True, 2.0), _scene("goal", True, 1.9)]
    chosen = select_scenes(many_misses + goals, youth=False)
    assert len(chosen) == 5
    assert sum(c.positive for c in chosen) == 2  # mixed despite higher-scored misses
    youth = select_scenes(many_misses + goals, youth=True)
    assert sum(not c.positive for c in youth) <= 2 and any(c.positive for c in youth)
    assert select_scenes(many_misses, youth=True) == []  # never only mistakes for children
    assert len(select_scenes(many_misses, youth=False)) == 3
    variety = select_scenes(
        [_scene("goal", True, 3.0), _scene("goal", True, 2.9), _scene("save", True, 2.0)],
        youth=False,
        n=2,
    )
    assert {c.reason for c in variety} == {"goal", "save"}


pytestmark_db = pytest.mark.usefixtures("clean_db")


@pytestmark_db
async def test_feed_flow(make_api: Callable[[], Api], outbox: MemoryEmailSender) -> None:
    coach = make_api()
    ids = await setup_club(coach)
    org, team = ids["org"], ids["team"]
    roster = f"/v1/orgs/{org}/teams/{team}/seasons/{ids['season']}/roster"
    lena = (
        await coach.post(
            roster,
            json={"first_name": "Lena", "last_name": "M", "jersey_number": 7, "birth_year": 1999},
        )
    ).json()
    nina = (
        await coach.post(
            roster,
            json={"first_name": "Nina", "last_name": "K", "jersey_number": 9, "birth_year": 2000},
        )
    ).json()
    consents = f"/v1/orgs/{org}/teams/{team}/players/{lena['player_id']}/consents"
    await coach.post(
        consents,
        json={
            "kind": "analysis",
            "given_by": "self",
            "given_by_name": "Lena M",
            "given_at": "2026-10-01T10:00:00+02:00",
        },
    )
    await coach.post(
        f"/v1/orgs/{org}/invitations",
        json={
            "email": "lena@hc-test.ch",
            "team_id": team,
            "team_role": "player",
            "player_id": lena["player_id"],
        },
    )
    token = re.search(r"/invite/([\w-]+)", outbox.outbox[-1].text)
    assert token
    player = make_api()
    await player.register("lena@hc-test.ch", name="Lena M", invitation_token=token.group(1))

    m = await new_match(coach, ids)
    ev = f"/v1/orgs/{org}/matches/{m['id']}/events"
    for i, (outcome, pid) in enumerate(
        [
            ("goal", lena),
            ("miss", lena),
            ("goal", lena),
            ("goal", nina),
            ("save", lena),
            ("goal", lena),
        ]
    ):
        r = await coach.post(
            ev,
            json={
                "type": "shot",
                "side": "own",
                "outcome": outcome,
                "t_ms": 60_000 * (i + 1),
                "player_id": pid["player_id"],
            },
        )
        assert r.status_code == 201
    await coach.post(
        ev,
        json={"type": "turnover", "side": "own", "t_ms": 500_000, "player_id": lena["player_id"]},
    )

    gen = await coach.post(f"/v1/orgs/{org}/matches/{m['id']}/feed/generate")
    assert gen.json() == {"players": 1}  # Nina has no analysis consent
    overview = (await coach.get(f"/v1/orgs/{org}/matches/{m['id']}/feed")).json()
    assert [p["name"] for p in overview] == ["Lena M"]
    scenes = overview[0]["items"]
    assert len(scenes) == 5 and {s["positive"] for s in scenes} == {True, False}
    await coach.patch(
        f"/v1/orgs/{org}/feed-items/{scenes[0]['id']}", json={"coach_comment": "Stark gelöst"}
    )

    notes = (await player.get(f"/v1/orgs/{org}/me/notifications")).json()
    assert any(n["kind"] == "feed_ready" for n in notes["items"])
    feeds = (await player.get(f"/v1/orgs/{org}/me/feeds")).json()
    assert [(f["match_id"], f["assessed"]) for f in feeds] == [(m["id"], False)]
    mine = (await player.get(f"/v1/orgs/{org}/matches/{m['id']}/feed/me")).json()
    assert mine["self_assessment"] is None
    assert all(s["coach_comment"] is None for s in mine["items"])  # self-assessment first
    assert mine["coach_comments_waiting"] == 1
    assessed = await player.put(
        f"/v1/orgs/{org}/matches/{m['id']}/self-assessment",
        json={"rating": 4, "text": "Gute Abschlüsse"},
    )
    assert assessed.status_code == 200
    assert assessed.json()["items"][0]["coach_comment"] == "Stark gelöst"
    assert (await player.get(f"/v1/orgs/{org}/me/feeds")).json()[0]["assessed"] is True
    overview = (await coach.get(f"/v1/orgs/{org}/matches/{m['id']}/feed")).json()
    assert overview[0]["self_assessment"]["rating"] == 4
    assert all(s["seen"] for s in overview[0]["items"])

    # the coach swaps a scene; players cannot see the team overview or others' feeds
    nina_goal = next(e for e in (await coach.get(ev)).json() if e["player_id"] == nina["player_id"])
    assert (
        await coach.put(
            f"/v1/orgs/{org}/feed-items/{scenes[1]['id']}/scene", json={"event_id": nina_goal["id"]}
        )
    ).status_code == 204
    assert (await player.get(f"/v1/orgs/{org}/matches/{m['id']}/feed")).status_code == 403
    other = await player.get(
        f"/v1/orgs/{org}/matches/{m['id']}/feed/me", params={"player_id": nina["player_id"]}
    )
    assert other.status_code == 404
    # a parent sees the child's scenes but cannot rate for the child
    await coach.post(
        f"/v1/orgs/{org}/invitations",
        json={
            "email": "mama@hc-test.ch",
            "team_id": team,
            "team_role": "parent",
            "player_id": lena["player_id"],
        },
    )
    ptoken = re.search(r"/invite/([\w-]+)", outbox.outbox[-1].text)
    assert ptoken
    parent = make_api()
    await parent.register("mama@hc-test.ch", invitation_token=ptoken.group(1))
    pf = (await parent.get(f"/v1/orgs/{org}/me/feeds")).json()
    assert [(f["relation"], f["player_first_name"]) for f in pf] == [("guardian", "Lena")]
    seen = await parent.get(
        f"/v1/orgs/{org}/matches/{m['id']}/feed/me", params={"player_id": lena["player_id"]}
    )
    assert seen.status_code == 200 and seen.json()["self_assessment"]["rating"] == 4
    rate = await parent.put(
        f"/v1/orgs/{org}/matches/{m['id']}/self-assessment",
        json={"rating": 1, "player_id": lena["player_id"]},
    )
    assert rate.status_code == 403
    # regeneration keeps the coach's comments on scenes that stay
    await coach.post(f"/v1/orgs/{org}/matches/{m['id']}/feed/generate")
    again = (await coach.get(f"/v1/orgs/{org}/matches/{m['id']}/feed")).json()[0]["items"]
    assert any(s["coach_comment"] == "Stark gelöst" for s in again)

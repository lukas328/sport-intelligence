"""Assignments and notifications (M7)."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

import pytest

from handball_api.core.email import MemoryEmailSender

from .conftest import Api, setup_club

pytestmark = pytest.mark.usefixtures("clean_db")


async def add_member(
    make_api: Callable[[], Api],
    coach: Api,
    ids: dict[str, Any],
    outbox: MemoryEmailSender,
    email: str,
    role: str = "player",
    name: str = "Test User",
    player_id: str | None = None,
) -> Api:
    body = {"email": email, "team_id": ids["team"], "team_role": role}
    if player_id:
        body["player_id"] = player_id
    await coach.post(f"/v1/orgs/{ids['org']}/invitations", json=body)
    token = re.search(r"/invite/([\w-]+)", outbox.outbox[-1].text)
    assert token
    api = make_api()
    assert (
        await api.register(email, name=name, invitation_token=token.group(1))
    ).status_code == 201
    return api


async def test_assignment_flow(make_api: Callable[[], Api], outbox: MemoryEmailSender) -> None:
    coach = make_api()
    ids = await setup_club(coach)
    org, team = ids["org"], ids["team"]
    base = f"/v1/orgs/{org}/teams/{team}/assignments"
    pl = (
        await coach.post(f"/v1/orgs/{org}/teams/{team}/playlists", json={"title": "Abwehr"})
    ).json()
    body = {"kind": "playlist", "target_id": pl["id"], "title": "Abwehrclips anschauen"}
    assert (await coach.post(base, json=body)).status_code == 409  # nobody to assign yet

    mia = await add_member(make_api, coach, ids, outbox, "mia@hc-test.ch")
    tim = await add_member(make_api, coach, ids, outbox, "tim@hc-test.ch", "goalkeeper")
    before = len(outbox.outbox)
    r = await coach.post(base, json={**body, "due_at": "2026-11-10T18:00:00+01:00"})
    assert r.status_code == 201, r.text
    a = r.json()
    assert (a["recipients"], a["done"]) == (2, 0)
    assert len(outbox.outbox) == before + 2
    assert "Abwehrclips anschauen" in outbox.outbox[-1].subject
    assert "Bis 10.11.2026" in outbox.outbox[-1].text
    # the playlist is now visible for players
    pls = (await mia.get(f"/v1/orgs/{org}/teams/{team}/playlists")).json()
    assert [p["title"] for p in pls] == ["Abwehr"]

    # players: list, notification, done
    mine = (await mia.get(f"/v1/orgs/{org}/me/assignments")).json()
    assert [m["title"] for m in mine] == ["Abwehrclips anschauen"]
    assert mine[0]["team_name"] == "Herren 1" and mine[0]["done_at"] is None
    notes = (await mia.get(f"/v1/orgs/{org}/me/notifications")).json()
    assert notes["unread"] == 1 and notes["items"][0]["kind"] == "assignment"
    assert notes["items"][0]["link"].endswith(f"/playlists/{pl['id']}")
    r = await mia.put(f"/v1/orgs/{org}/assignments/{a['id']}/status", json={"done": True})
    assert r.json()["done"] == 1 and r.json()["done_at"]
    # coach sees progress and gets a notification
    listing = (await coach.get(base)).json()
    progress = {p["user_id"]: p["done_at"] is not None for p in listing[0]["progress"]}
    assert sorted(progress.values()) == [False, True]
    cn = (await coach.get(f"/v1/orgs/{org}/me/notifications")).json()
    assert cn["items"][0]["kind"] == "assignment_done"
    assert (await coach.post(f"/v1/orgs/{org}/me/notifications/read", json={})).status_code == 204
    assert (await coach.get(f"/v1/orgs/{org}/me/notifications")).json()["unread"] == 0
    note_id = notes["items"][0]["id"]
    await mia.post(f"/v1/orgs/{org}/me/notifications/read", json={"ids": [note_id]})
    assert (await mia.get(f"/v1/orgs/{org}/me/notifications")).json()["unread"] == 0

    # rights and validation
    assert (await mia.post(base, json=body)).status_code == 403
    assert (await mia.get(base)).status_code == 403
    assert (
        await coach.post(base, json={**body, "target_id": "00000000-0000-0000-0000-000000000001"})
    ).status_code == 422
    assert (await coach.post(base, json={**body, "target_id": "nope"})).status_code == 422
    stranger = "00000000-0000-0000-0000-000000000002"
    assert (await coach.post(base, json={**body, "user_ids": [stranger]})).status_code == 422
    drill = await coach.post(
        base,
        json={
            "kind": "drill",
            "target_id": "finishing_wings",
            "title": "Flügelwürfe",
            "user_ids": [tim.user["id"]],
            "notify_email": False,
        },
    )
    assert drill.status_code == 201 and drill.json()["recipients"] == 1
    assert (
        await tim.put(f"/v1/orgs/{org}/assignments/{a['id']}/status", json={"done": False})
    ).json()["done_at"] is None
    assert (
        await mia.put(
            f"/v1/orgs/{org}/assignments/{drill.json()['id']}/status", json={"done": True}
        )
    ).status_code == 404
    assert (await mia.delete(f"/v1/orgs/{org}/assignments/{a['id']}")).status_code == 403
    assert (await coach.delete(f"/v1/orgs/{org}/assignments/{a['id']}")).status_code == 204
    assert (await mia.get(f"/v1/orgs/{org}/me/assignments")).json() == []


async def test_assignment_progress_for_staff(
    make_api: Callable[[], Api], outbox: MemoryEmailSender
) -> None:
    coach = make_api()
    ids = await setup_club(coach)
    org, team = ids["org"], ids["team"]
    roster = f"/v1/orgs/{org}/teams/{team}/seasons/{ids['season']}/roster"
    entry = (await coach.post(roster, json={"first_name": "Alia", "last_name": "Test"})).json()
    alia = await add_member(
        make_api,
        coach,
        ids,
        outbox,
        "alia@hc-test.ch",
        name="Alia Test",
        player_id=entry["player_id"],
    )
    bea = await add_member(make_api, coach, ids, outbox, "bea@hc-test.ch", name="Bea Probe")
    await add_member(make_api, coach, ids, outbox, "cleo@hc-test.ch", "goalkeeper", "Cleo Fiktiv")
    analyst = await add_member(make_api, coach, ids, outbox, "an@hc-test.ch", "analyst", "Ana")
    manager = await add_member(make_api, coach, ids, outbox, "tm@hc-test.ch", "team_manager")
    body = {"kind": "drill", "target_id": "finishing_wings", "title": "Flügelwürfe"}
    created = await coach.post(
        f"/v1/orgs/{org}/teams/{team}/assignments", json={**body, "notify_email": False}
    )
    assert created.status_code == 201, created.text
    a = created.json()
    assert (a["recipients"], a["done"]) == (3, 0)
    assert [p["name"] for p in a["still_open"]] == ["Alia Test", "Bea Probe", "Cleo Fiktiv"]
    detail_url = f"/v1/orgs/{org}/assignments/{a['id']}"

    r = await alia.put(f"{detail_url}/status", json={"done": True})
    # a player's counts cover only their own status
    assert (r.json()["recipients"], r.json()["done"]) == (1, 1)
    assert r.json()["progress"] is None and r.json()["still_open"] is None
    mine = (await bea.get(f"/v1/orgs/{org}/me/assignments")).json()
    assert (mine[0]["recipients"], mine[0]["done"]) == (1, 0)
    assert mine[0]["progress"] is None and mine[0]["still_open"] is None

    # staff: "1 von 3 erledigt" and who is still open, in the list and the detail
    for staff in (coach, analyst):
        d = (await staff.get(detail_url)).json()
        assert (d["recipients"], d["done"]) == (3, 1)
        assert [p["name"] for p in d["still_open"]] == ["Bea Probe", "Cleo Fiktiv"]
        done = [p for p in d["progress"] if p["done_at"]]
        assert [p["name"] for p in done] == ["Alia Test"]
        assert done[0]["player_id"] == entry["player_id"] and done[0]["seen_at"]
        assert all(p["player_id"] is None for p in d["still_open"])
    listing = (await coach.get(f"/v1/orgs/{org}/teams/{team}/assignments")).json()
    assert listing[0]["done"] == 1 and len(listing[0]["still_open"]) == 2

    # players never see other players' progress; outside the video staff no detail
    for api in (alia, bea, manager):
        assert (await api.get(detail_url)).status_code == 403
    assert (await coach.get(f"/v1/orgs/{org}/assignments/{ids['team']}")).status_code == 404
    other = make_api()
    await setup_club(other, "other@hc-test.ch")
    assert (await other.get(f"/v1/orgs/{org}/assignments/{a['id']}")).status_code == 404

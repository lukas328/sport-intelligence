"""Drill library: static drills and the club's own drills in one list."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from handball_api.core.email import MemoryEmailSender
from handball_api.services.drills import library

from .conftest import Api, setup_club
from .test_roster import _join

pytestmark = pytest.mark.usefixtures("clean_db")

DRILL = {
    "name": "Kreuzen im Rückraum",
    "setup": "Drei Rückraumspieler kreuzen, der Kreisläufer sperrt.",
    "coaching": "Tempo vor dem Kreuzen, Blick zum Kreis.",
    "minutes": 20,
    "players": "6-10",
    "level": "advanced",
    "focus": ["back_court", "Kreuzen", "back_court"],
}


async def test_library_and_own_drills(
    make_api: Callable[[], Api], outbox: MemoryEmailSender
) -> None:
    admin = make_api()
    ids = await setup_club(admin)
    org = f"/v1/orgs/{ids['org']}"
    team_a = f"{org}/teams/{ids['team']}"
    r = await admin.post(f"{org}/teams", json={"name": "U17", "gender": "women"})
    ids_b = {**ids, "team": r.json()["id"]}
    team_b = f"{org}/teams/{ids_b['team']}"
    coach_a = await _join(make_api, admin, ids, outbox, "trainer-a@hc-test.ch", "coach")
    coach_b = await _join(make_api, admin, ids_b, outbox, "trainer-b@hc-test.ch", "coach")
    player_a = await _join(make_api, admin, ids, outbox, "spielerin@hc-test.ch")
    player_b = await _join(make_api, admin, ids_b, outbox, "junior@hc-test.ch")

    # the library alone, in the asked language
    listed = (await coach_a.get(f"{team_a}/drills")).json()
    assert len(listed) == len(library()) and {d["source"] for d in listed} == {"library"}
    wings = listed[0]
    assert wings["id"] == "finishing_wings" and wings["name"] == "Flügelwürfe unter Druck"
    assert wings["own"] is False and wings["editable"] is False and wings["shared"] is True
    assert wings["players"] == "6-12" and wings["focus"] == ["finishing", "wings"]
    fr = (await coach_a.get(f"{team_a}/drills?lang=fr")).json()[0]
    assert fr["name"] == "Tirs à l'aile sous pression"
    assert (await coach_a.get(f"{team_a}/drills?lang=it")).status_code == 422
    one = (await player_a.get(f"{org}/drills/finishing_wings?lang=en")).json()
    assert one["name"] == "Wing shots under pressure"
    assert (await coach_a.get(f"{org}/drills/nope")).status_code == 404

    # an own drill of team A, not shared
    r = await coach_a.post(f"{team_a}/drills", json=DRILL)
    assert r.status_code == 201, r.text
    own = r.json()
    assert own["source"] == "club" and own["own"] is True and own["editable"] is True
    assert own["shared"] is False and own["team_name"] == "Herren 1"
    assert own["focus"] == ["back_court", "Kreuzen"] and own["level"] == "advanced"
    listed = (await coach_a.get(f"{team_a}/drills")).json()
    assert listed[0]["id"] == own["id"] and len(listed) == len(library()) + 1
    for bad in (
        {**DRILL, "minutes": 0},
        {**DRILL, "minutes": 181},
        {**DRILL, "name": "  "},
        {**DRILL, "players": "viele"},
        {**DRILL, "level": "expert"},
        {**DRILL, "focus": [f"t{i}" for i in range(11)]},
        {**DRILL, "setup": "x" * 2001},
    ):
        assert (await coach_a.post(f"{team_a}/drills", json=bad)).status_code == 422, bad

    # team B does not see it yet
    assert [d["source"] for d in (await coach_b.get(f"{team_b}/drills")).json()] == [
        "library"
    ] * len(library())
    assert (await coach_b.get(f"{org}/drills/{own['id']}")).status_code == 404
    assert (await coach_b.put(f"{org}/drills/{own['id']}", json=DRILL)).status_code == 404
    assert (await coach_b.get(f"{team_a}/drills")).status_code == 404  # not B's team

    # players of team A read it, but cannot write
    seen = (await player_a.get(f"{org}/drills/{own['id']}")).json()
    assert seen["name"] == DRILL["name"] and seen["editable"] is False
    assert (await player_a.post(f"{team_a}/drills", json=DRILL)).status_code == 403
    assert (await player_a.put(f"{org}/drills/{own['id']}", json=DRILL)).status_code == 403
    assert (await player_a.delete(f"{org}/drills/{own['id']}")).status_code == 403

    # shared within the club: every team sees it, only team A changes it
    r = await coach_a.put(
        f"{org}/drills/{own['id']}", json={**DRILL, "shared": True, "minutes": 25}
    )
    assert r.status_code == 200 and r.json()["shared"] is True and r.json()["minutes"] == 25
    in_b = (await coach_b.get(f"{team_b}/drills")).json()
    assert in_b[0]["id"] == own["id"] and in_b[0]["editable"] is False
    assert in_b[0]["team_name"] == "Herren 1"
    assert (await player_b.get(f"{org}/drills/{own['id']}")).status_code == 200
    assert (await coach_b.put(f"{org}/drills/{own['id']}", json=DRILL)).status_code == 403
    assert (await coach_b.delete(f"{org}/drills/{own['id']}")).status_code == 403
    b_own = await coach_b.post(
        f"{team_b}/drills", json={"name": "Torhüter 1 gegen 1", "minutes": 10}
    )
    assert b_own.status_code == 201 and b_own.json()["players"] is None
    names = [d["name"] for d in (await coach_a.get(f"{team_a}/drills")).json() if d["own"]]
    assert names == [DRILL["name"]]  # B's drill is not shared
    names = [d["name"] for d in (await coach_b.get(f"{team_b}/drills")).json() if d["own"]]
    assert names == [DRILL["name"], "Torhüter 1 gegen 1"]
    # the club admin edits drills of every team
    listed = (await admin.get(f"{team_b}/drills")).json()
    assert all(d["editable"] for d in listed if d["own"])

    # an own drill goes into a session and an assignment like a library drill
    session = await coach_a.post(
        f"{team_a}/sessions",
        json={
            "on_date": "2040-09-04",
            "drills": [{"drill_id": own["id"], "name": DRILL["name"], "minutes": 25}],
        },
    )
    assert session.status_code == 201
    r = await coach_a.post(
        f"{team_a}/assignments",
        json={"kind": "drill", "target_id": own["id"], "title": "Lesen", "notify_email": False},
    )
    assert r.status_code == 201, r.text

    # another club reaches nothing
    other = make_api()
    oid = await setup_club(other, "andere@hc-test.ch")
    assert (await other.get(f"{org}/drills/{own['id']}")).status_code == 404
    assert (await other.get(f"/v1/orgs/{oid['org']}/drills/{own['id']}")).status_code == 404
    mixed = f"/v1/orgs/{oid['org']}/drills/{own['id']}"
    assert (await other.put(mixed, json=DRILL)).status_code == 404
    assert (await other.delete(mixed)).status_code == 404
    other_list = (await other.get(f"/v1/orgs/{oid['org']}/teams/{oid['team']}/drills")).json()
    assert not [d for d in other_list if d["own"]]

    # deleting keeps the session's snapshot
    assert (await coach_a.delete(f"{org}/drills/{own['id']}")).status_code == 204
    assert (await coach_a.get(f"{org}/drills/{own['id']}")).status_code == 404
    assert own["id"] not in [d["id"] for d in (await coach_b.get(f"{team_b}/drills")).json()]
    kept = (await coach_a.get(f"{org}/sessions/{session.json()['id']}")).json()
    assert kept["drills"][0]["drill_id"] == own["id"]

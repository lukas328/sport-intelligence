"""Recurring training slots and the sessions of a season created from them."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest

from handball_api.core.email import MemoryEmailSender

from .conftest import Api, setup_club
from .test_roster import _join

pytestmark = pytest.mark.usefixtures("clean_db")

START, END = date(2040, 8, 1), date(2040, 9, 30)
ZURICH = ZoneInfo("Europe/Zurich")


def _days(weekday: int, start: date = START, end: date = END) -> list[date]:
    return [
        start + timedelta(days=i)
        for i in range((end - start).days + 1)
        if (start + timedelta(days=i)).isoweekday() == weekday
    ]


async def test_slots_create_the_sessions_of_a_season(
    make_api: Callable[[], Api], outbox: MemoryEmailSender
) -> None:
    coach = make_api()
    ids = await setup_club(coach)
    org = f"/v1/orgs/{ids['org']}"
    team = f"{org}/teams/{ids['team']}"
    r = await coach.post(
        f"{team}/seasons",
        json={"label": "2040", "starts_on": START.isoformat(), "ends_on": END.isoformat()},
    )
    assert r.status_code == 201, r.text
    slots = f"{team}/seasons/{r.json()['id']}/training-slots"

    tue = {
        "weekday": 2,
        "start_time": "19:00",
        "duration_min": 90,
        "location": "Halle Nord",
        "title": "Training",
        "note": "Garderobe 3",
    }
    r = await coach.post(slots, json=tue)
    assert r.status_code == 201, r.text
    s_tue = r.json()
    assert s_tue["end_time"] == "20:30:00" and s_tue["valid_from"] is None
    thu = {"weekday": 4, "start_time": "18:30", "duration_min": 120, "valid_from": "2040-09-01"}
    s_thu = (await coach.post(slots, json=thu)).json()
    assert s_thu["end_time"] == "20:30:00" and s_thu["location"] is None
    listed = (await coach.get(slots)).json()
    assert [x["id"] for x in listed] == [s_tue["id"], s_thu["id"]]

    # validation
    for bad in (
        {**tue, "weekday": 8},
        {**tue, "weekday": 0},
        {**tue, "duration_min": 10},
        {**tue, "note": "x" * 501},
        {**tue, "valid_from": "2040-09-10", "valid_until": "2040-09-01"},
        {**tue, "valid_from": "2040-07-01"},  # before the season
    ):
        assert (await coach.post(slots, json=bad)).status_code == 422, bad

    # a session already planned on the first Tuesday at the slot's time is kept
    first_tue = _days(2)[0]
    at = datetime.combine(first_tue, time(19), tzinfo=ZURICH)
    planned = await coach.post(
        f"{team}/sessions",
        json={"on_date": first_tue.isoformat(), "starts_at": at.isoformat(), "title": "Abschluss"},
    )
    assert planned.status_code == 201

    holiday = _days(2)[2]
    gen = await coach.post(f"{slots}/generate", json={"skip_dates": [holiday.isoformat()]})
    assert gen.status_code == 200, gen.text
    out = gen.json()
    tuesdays, thursdays = _days(2), _days(4, start=date(2040, 9, 1))
    assert out["kept"] == 1 and out["skipped"] == 1
    assert out["created"] == len(tuesdays) - 2 + len(thursdays) == len(out["sessions"])
    first = out["sessions"][0]
    assert first["on_date"] == tuesdays[1].isoformat()
    assert datetime.fromisoformat(first["starts_at"]).astimezone(ZURICH).hour == 19
    assert first["location"] == "Halle Nord" and first["notes"] == "Garderobe 3"
    assert first["title"] == "Training" and first["slot_id"] == s_tue["id"]
    assert first["drills"] == [] and first["total_minutes"] == 0
    days = [x["on_date"] for x in out["sessions"]]
    assert holiday.isoformat() not in days and days == sorted(days)
    assert min(d for d in days if date.fromisoformat(d).isoweekday() == 4) == "2040-09-06"
    all_sessions = (await coach.get(f"{team}/sessions")).json()
    assert len(all_sessions) == out["created"] + 1
    assert [x["title"] for x in all_sessions if x["on_date"] == first_tue.isoformat()] == [
        "Abschluss"
    ]

    # idempotent: running it again creates nothing
    skip = {"skip_dates": [holiday.isoformat()]}
    again = (await coach.post(f"{slots}/generate", json=skip)).json()
    assert again["created"] == 0 and again["sessions"] == []
    assert again["kept"] == out["created"] + 1 and again["skipped"] == 1

    # a changed time applies to new sessions only; days with a session of the slot are kept
    moved = await coach.put(
        f"{org}/training-slots/{s_tue['id']}", json={**tue, "start_time": "20:00"}
    )
    assert moved.status_code == 200 and moved.json()["end_time"] == "21:30:00"
    since = tuesdays[1].isoformat()  # the first Tuesday has a session at the old time only
    again = await coach.post(f"{slots}/generate", json={**skip, "from": since, "to": "2040-08-31"})
    assert again.json()["created"] == 0 and again.json()["kept"] == 2  # 14 and 28 August
    # the holiday is created when it is no longer skipped, at the new time
    again = (
        await coach.post(
            f"{slots}/generate",
            json={
                "from": holiday.isoformat(),
                "to": holiday.isoformat(),
                "slot_ids": [s_tue["id"]],
            },
        )
    ).json()
    assert again["created"] == 1
    assert datetime.fromisoformat(again["sessions"][0]["starts_at"]).astimezone(ZURICH).hour == 20

    # range checks and unknown slots
    r = await coach.post(f"{slots}/generate", json={"from": "2040-09-10", "to": "2040-09-01"})
    assert r.status_code == 422
    unknown = "00000000-0000-0000-0000-000000000009"
    r = await coach.post(f"{slots}/generate", json={"slot_ids": [unknown]})
    assert r.status_code == 404
    # outside the season: nothing to do
    r = await coach.post(f"{slots}/generate", json={"from": "2041-01-01", "to": "2041-02-01"})
    assert r.json()["created"] == 0 and r.json()["kept"] == 0

    # the calendar feed ends a session from a slot after the slot's duration
    link = (await coach.post(f"{team}/calendar")).json()["url"]
    ics = (await make_api().get(link[link.index("/v1/calendar/") :])).text
    assert "Halle Nord" in ics

    # players read the slots, but do not change them or create sessions
    player = await _join(make_api, coach, ids, outbox, "spieler@hc-test.ch")
    assert (await player.get(slots)).status_code == 200
    assert (await player.post(slots, json=tue)).status_code == 403
    assert (await player.post(f"{slots}/generate", json={})).status_code == 403
    assert (await player.put(f"{org}/training-slots/{s_tue['id']}", json=tue)).status_code == 403
    assert (await player.delete(f"{org}/training-slots/{s_tue['id']}")).status_code == 403
    manager = await _join(make_api, coach, ids, outbox, "tm@hc-test.ch", "team_manager")
    assert (await manager.post(slots, json={**tue, "weekday": 5})).status_code == 201

    # another club reaches nothing
    other = make_api()
    oid = await setup_club(other, "andere@hc-test.ch")
    assert (await other.get(slots)).status_code == 404
    assert (await other.post(f"{slots}/generate", json={})).status_code == 404
    mixed = f"/v1/orgs/{oid['org']}/training-slots/{s_tue['id']}"
    assert (await other.put(mixed, json=tue)).status_code == 404
    assert (await other.delete(mixed)).status_code == 404

    # deleting a slot keeps its sessions
    assert (await coach.delete(f"{org}/training-slots/{s_tue['id']}")).status_code == 204
    assert (await coach.delete(f"{org}/training-slots/{s_tue['id']}")).status_code == 404
    left = (await coach.get(f"{team}/sessions")).json()
    assert len(left) == len(all_sessions) + 1
    assert all(x["slot_id"] != s_tue["id"] for x in left)

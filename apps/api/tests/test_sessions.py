"""Training planning, attendance, calendar feed (5.7) and from problem to training (5.6)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from typing import Any

import asyncpg
import pytest

from .conftest import Api, setup_club
from .test_assistant import seed
from .test_matches import new_match
from .test_official_report import recorded, reported_clip  # noqa: F401

pytestmark = pytest.mark.usefixtures("clean_db")

DRILLS = [
    {
        "drill_id": "wing-finish",
        "name": "Flügelabschluss",
        "minutes": 20,
        "focus": ["wings"],
        "setup": "Zwei Reihen am Flügel",
        "coaching": "Winkel öffnen",
    },
    {"drill_id": "free", "name": "Spiel 6 gegen 6", "minutes": 25, "note": "Mit Zeitstrafen"},
]


async def test_sessions_pdf_calendar_and_import(
    make_api: Callable[[], Api], owner_conn: asyncpg.Connection
) -> None:
    api = make_api()
    ids = await setup_club(api)
    org, team = ids["org"], ids["team"]
    tomorrow = (datetime.now(UTC) + timedelta(days=1)).date()
    body = {
        "on_date": tomorrow.isoformat(),
        "starts_at": f"{tomorrow.isoformat()}T19:00:00+01:00",
        "title": "Abschluss",
        "location": "Halle Nord",
        "drills": DRILLS,
    }
    r = await api.post(f"/v1/orgs/{org}/teams/{team}/sessions", json=body)
    assert r.status_code == 201, r.text
    s = r.json()
    assert s["total_minutes"] == 45 and s["drills"][0]["setup"] == "Zwei Reihen am Flügel"
    bad = {**body, "drills": [{**DRILLS[0], "minutes": 0}]}
    assert (await api.post(f"/v1/orgs/{org}/teams/{team}/sessions", json=bad)).status_code == 422
    upd = await api.put(f"/v1/orgs/{org}/sessions/{s['id']}", json={**body, "drills": DRILLS[:1]})
    assert upd.json()["total_minutes"] == 20
    listed = (
        await api.get(f"/v1/orgs/{org}/teams/{team}/sessions?from={tomorrow.isoformat()}")
    ).json()
    assert [x["id"] for x in listed] == [s["id"]]
    pdf = await api.get(f"/v1/orgs/{org}/sessions/{s['id']}/pdf?lang=fr")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")

    # calendar: a match and the session; a new link invalidates the old one
    await new_match(
        api, ids, opponent_name="TV Kalender", kickoff_at=f"{tomorrow.isoformat()}T15:00:00+01:00"
    )
    link = (await api.post(f"/v1/orgs/{org}/teams/{team}/calendar")).json()["url"]
    path = link[link.index("/v1/calendar/") :]
    anon = make_api()
    feed = await anon.get(path)
    assert feed.status_code == 200 and feed.headers["content-type"].startswith("text/calendar")
    text = feed.text
    assert text.count("BEGIN:VEVENT") == 2 and "TV Kalender" in text and "Abschluss" in text
    assert "Halle Nord" in text
    second = (await api.post(f"/v1/orgs/{org}/teams/{team}/calendar")).json()["url"]
    assert (await anon.get(path)).status_code == 404
    assert (await api.delete(f"/v1/orgs/{org}/teams/{team}/calendar")).status_code == 204
    assert (await anon.get(second[second.index("/v1/calendar/") :])).status_code == 404

    # ICS import: known UIDs are updated, not duplicated
    ics = (
        "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//Spond//EN\r\n"
        "BEGIN:VEVENT\r\nUID:spond-1\r\nSUMMARY:Training\r\nDTSTART:20261110T180000Z\r\n"
        "DTEND:20261110T193000Z\r\nLOCATION:Halle Süd\r\nEND:VEVENT\r\n"
        "BEGIN:VEVENT\r\nUID:spond-2\r\nSUMMARY:Athletik\r\nDTSTART;VALUE=DATE:20261112\r\nEND:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    ).encode()
    url = f"/v1/orgs/{org}/teams/{team}/sessions/import"
    first = await api.post(url, files={"file": ("cal.ics", ics, "text/calendar")})
    assert first.json() == {"created": 2, "updated": 0}
    again = await api.post(url, files={"file": ("cal.ics", ics, "text/calendar")})
    assert again.json() == {"created": 0, "updated": 2}
    imported = (
        await api.get(f"/v1/orgs/{org}/teams/{team}/sessions?from=2026-11-10&to=2026-11-12")
    ).json()
    assert {x["title"] for x in imported} == {"Training", "Athletik"}
    assert next(x for x in imported if x["title"] == "Training")["location"] == "Halle Süd"
    assert (await api.delete(f"/v1/orgs/{org}/sessions/{s['id']}")).status_code == 204


async def test_attendance_replies_and_records(
    make_api: Callable[[], Api], owner_conn: asyncpg.Connection
) -> None:
    api = make_api()
    ids = await setup_club(api)
    org, team, season = ids["org"], ids["team"], ids["season"]
    roster = f"/v1/orgs/{org}/teams/{team}/seasons/{season}/roster"
    lena = (
        await api.post(roster, json={"first_name": "Lena", "last_name": "M", "jersey_number": 7})
    ).json()["player_id"]
    kid = (
        await api.post(roster, json={"first_name": "Tim", "last_name": "K", "jersey_number": 9})
    ).json()["player_id"]
    other = (
        await api.post(roster, json={"first_name": "Ola", "last_name": "N", "jersey_number": 3})
    ).json()["player_id"]
    user_id = await owner_conn.fetchval("SELECT id FROM users LIMIT 1")
    # the coach is also the player Lena (self) and the parent of Tim
    await owner_conn.execute("UPDATE players SET user_id = $1 WHERE id = $2::uuid", user_id, lena)
    await owner_conn.execute(
        "INSERT INTO guardianships (id, organization_id, user_id, player_id) "
        "VALUES (gen_random_uuid(), $1::uuid, $2, $3::uuid)",
        org,
        user_id,
        kid,
    )
    soon = (datetime.now(UTC) + timedelta(days=2)).date()
    s = (
        await api.post(f"/v1/orgs/{org}/teams/{team}/sessions", json={"on_date": soon.isoformat()})
    ).json()
    m = await new_match(
        api, ids, opponent_name="HC Test", kickoff_at=f"{soon.isoformat()}T18:00:00+01:00"
    )

    schedule = (await api.get(f"/v1/orgs/{org}/me/schedule")).json()
    assert {(i["kind"], i["player_name"], i["relation"]) for i in schedule} == {
        ("session", "Lena", "self"),
        ("session", "Tim", "guardian"),
        ("match", "Lena", "self"),
        ("match", "Tim", "guardian"),
    }
    reply = f"/v1/orgs/{org}/me/attendance"
    assert (
        await api.put(
            reply, json={"kind": "session", "id": s["id"], "player_id": lena, "response": "yes"}
        )
    ).status_code == 200
    r = await api.put(
        reply,
        json={
            "kind": "match",
            "id": m["id"],
            "player_id": kid,
            "response": "no",
            "reason": "Ferien",
        },
    )
    assert r.status_code == 200
    assert (
        await api.put(
            reply, json={"kind": "session", "id": s["id"], "player_id": other, "response": "yes"}
        )
    ).status_code == 403

    rows = (await api.get(f"/v1/orgs/{org}/attendance/session/{s['id']}")).json()
    assert {x["name"]: x["response"] for x in rows} == {
        "Lena M": "yes",
        "Tim K": None,
        "Ola N": None,
    }
    rec = await api.put(
        f"/v1/orgs/{org}/attendance/session/{s['id']}",
        json={
            "records": [
                {"player_id": lena, "status": "present"},
                {"player_id": other, "status": "excused", "reason": "Schule"},
            ]
        },
    )
    after = {x["name"]: (x["response"], x["status"], x["reason"]) for x in rec.json()}
    assert after["Lena M"] == ("yes", "present", None) and after["Ola N"] == (
        None,
        "excused",
        "Schule",
    )
    match_rows = (await api.get(f"/v1/orgs/{org}/attendance/match/{m['id']}")).json()
    assert {x["name"]: x["response"] for x in match_rows}["Tim K"] == "no"
    bad = await api.put(
        f"/v1/orgs/{org}/attendance/session/{s['id']}",
        json={
            "records": [{"player_id": "00000000-0000-0000-0000-000000000001", "status": "present"}]
        },
    )
    assert bad.status_code == 422
    # replies close once the day is over
    await owner_conn.execute("UPDATE training_sessions SET on_date = $1", date(2026, 1, 5))
    r = await api.put(
        reply, json={"kind": "session", "id": s["id"], "player_id": lena, "response": "no"}
    )
    assert r.status_code == 422


async def test_focus_from_insight_with_followup(
    make_api: Callable[[], Api], owner_conn: asyncpg.Connection, query_counter: list[str]
) -> None:
    api = make_api()
    ids = await seed(api, owner_conn)
    org, team = ids["org"], ids["team"]
    newest = await owner_conn.fetchval(
        "SELECT id::text FROM matches ORDER BY kickoff_at DESC LIMIT 1"
    )
    insights = (await api.get(f"/v1/orgs/{org}/matches/{newest}/insights")).json()["insights"]
    from handball_api.services.focus import FOLLOW, _rule

    followable = [i for i in insights if _rule(i["key"]) in FOLLOW and "player" not in i["key"]]
    assert followable, [i["key"] for i in insights]
    item = followable[0]
    body: dict[str, Any] = {
        "insight_key": item["key"],
        "params": item["params"],
        "title": "Fokus Abschluss",
        "session": {"on_date": "2026-11-10", "drills": DRILLS},
        "playlist": True,
        "assignment": True,
    }
    query_counter.clear()
    r = await api.post(f"/v1/orgs/{org}/matches/{newest}/focus", json=body)
    assert r.status_code == 201, r.text
    plan = r.json()
    inserts = sum(q.lstrip().startswith("INSERT INTO clips") for q in query_counter)
    assert plan["metric"] and plan["session_id"] and plan["playlist_id"]
    # nobody in the seeded team has an account: no assignment, the rest is created
    assert plan["assignment_id"] is None
    assert plan["focus"]
    items = await owner_conn.fetchval(
        "SELECT count(*) FROM playlist_items WHERE playlist_id = $1::uuid", plan["playlist_id"]
    )
    assert items > 1 and inserts == 1  # all clips in one statement, not one per clip
    session = (await api.get(f"/v1/orgs/{org}/sessions/{plan['session_id']}")).json()
    assert session["total_minutes"] == 45 and session["title"] == "Fokus Abschluss"
    bad = {**body, "params": {"zone": "nowhere"}}
    assert (await api.post(f"/v1/orgs/{org}/matches/{newest}/focus", json=bad)).status_code == 422

    listed = (await api.get(f"/v1/orgs/{org}/teams/{team}/focus")).json()
    f = listed[0]["followup"]
    # created today: the seeded matches all lie before
    assert f["before"]["matches"] == 5 and f["after"]["matches"] == 0 and f["trend"] is None
    assert "not proof" in f["note"]
    # as if the focus had started after the fourth match: four before, four after
    await owner_conn.execute("UPDATE focus_plans SET created_at = '2026-09-27T12:00:00Z'")
    f = (await api.get(f"/v1/orgs/{org}/teams/{team}/focus")).json()[0]["followup"]
    assert f["before"]["matches"] == 4 and f["after"]["matches"] == 4
    assert f["trend"] in ("better", "worse", "same")
    closed = (await api.post(f"/v1/orgs/{org}/focus/{plan['id']}/close")).json()
    assert closed["closed_at"]


@pytest.mark.usefixtures("recorded")
async def test_focus_playlist_skips_events_outside_the_video(
    make_api: Callable[[], Api], owner_conn: asyncpg.Connection, query_counter: list[str]
) -> None:
    """A clip of five minutes from mid-half with the whole game's official report: the events
    before the video (negative time) and after it have no scene; a focus playlist used to cut a
    clip ending before 0 s and failed with a server error."""
    api = make_api()
    ids = await setup_club(api)
    m, _ = await reported_clip(api, ids)
    base = f"/v1/orgs/{ids['org']}/matches/{m['id']}"
    insights = (await api.get(f"{base}/insights")).json()["insights"]
    assert insights
    plans = 0
    for item in insights:
        body = {"insight_key": item["key"], "params": item["params"], "playlist": True}
        query_counter.clear()
        r = await api.post(f"{base}/focus", json=body)
        assert r.status_code in (201, 422), (item["key"], r.status_code, r.text)
        plans += r.status_code == 201
        # all clips of the playlist in one statement, not a round trip per clip
        assert sum(q.lstrip().startswith("INSERT INTO clips") for q in query_counter) <= 1
    assert plans
    windows = await owner_conn.fetch(
        "SELECT start_ms, end_ms FROM clips WHERE match_id = $1::uuid", m["id"]
    )
    assert all(0 <= w["start_ms"] < w["end_ms"] <= 300_000 for w in windows), windows

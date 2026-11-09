"""Names from the official data in the attendance list of sessions and matches.

The roster list shows entries taken over from the official data only to the team's organisers
until the person joins or consents (`services/roster.py`); the attendance list, which analysts
and assistant coaches (goalkeeper and athletic coach) also see (Action.TRAINING_WRITE), follows
the same rule: such entries are left out for them, and recording attendance for one is refused
like a player outside the roster (docs/plans/federation-onboarding.md, Datenschutz)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest

from handball_api.core.email import MemoryEmailSender

from .conftest import Api
from .test_official import base, claim, coach, hch, invite, suggestions

pytestmark = pytest.mark.usefixtures("clean_db", "hch")
__all__ = ["hch"]  # the recorded handball.ch answers (autouse in test_official)


async def test_official_names_in_attendance_follow_the_roster_rule(
    make_api: Callable[[], Api], outbox: MemoryEmailSender
) -> None:
    api = await coach(make_api)
    c = await claim(api)
    org = c["organization_id"]
    roster = {s["payload"]["first_name"]: s for s in await suggestions(api, c, "roster_add")}
    ids = {}
    for name in ("Luca", "Noah"):
        r = await api.post(base(c) + f"/official/suggestions/{roster[name]['id']}/accept")
        assert r.status_code == 200, r.text
        ids[name] = r.json()["player_id"]
    season = (await api.get(base(c))).json()["current_season"]["id"]
    own = await api.post(
        base(c) + f"/seasons/{season}/roster",
        json={"first_name": "Mia", "last_name": "Eigen", "jersey_number": 99},
    )
    assert own.status_code == 201, own.text
    mia = own.json()["player_id"]
    soon = (datetime.now(UTC) + timedelta(days=2)).date().isoformat()
    s = await api.post(base(c) + "/sessions", json={"on_date": soon})
    assert s.status_code == 201, s.text
    session = f"/v1/orgs/{org}/attendance/session/{s.json()['id']}"
    matches = (await api.get(base(c) + "/matches")).json()
    assert matches
    match = f"/v1/orgs/{org}/attendance/match/{matches[0]['id']}"
    analyst = await invite(api, make_api, outbox, c, "analyst")
    # the assistant coaches see the attendance list too, under the same rule
    assistants = [
        await invite(api, make_api, outbox, c, role)
        for role in ("goalkeeper_coach", "athletic_coach")
    ]
    staff = [analyst, *assistants]

    async def seen(who: Api, url: str) -> dict[str, tuple[str, int | None]]:
        r = await who.get(url)
        assert r.status_code == 200, r.text
        return {x["player_id"]: (x["name"], x["number"]) for x in r.json()}

    # the coach organises the team: every entry, with its name
    for url in (session, match):
        rows = await seen(api, url)
        assert {ids["Luca"], ids["Noah"], mia} <= set(rows)
        assert rows[ids["Luca"]][0].startswith("Luca")
    # analyst and assistant coaches see the own entry, none of the official-only ones
    # (no name, no number), and cannot record attendance for one
    for who in staff:
        for url in (session, match):
            rows = await seen(who, url)
            assert mia in rows and not {ids["Luca"], ids["Noah"]} & set(rows)
            assert not any(name.startswith(("Luca", "Noah")) for name, _ in rows.values())
        hidden = await who.put(
            session, json={"records": [{"player_id": ids["Luca"], "status": "present"}]}
        )
        assert hidden.status_code == 422, hidden.text
    # the coach records for everyone; the analyst's answer still leaves the hidden entry out
    r = await api.put(session, json={"records": [{"player_id": ids["Luca"], "status": "present"}]})
    assert r.status_code == 200, r.text
    r = await analyst.put(session, json={"records": [{"player_id": mia, "status": "present"}]})
    assert r.status_code == 200, r.text
    assert ids["Luca"] not in {x["player_id"] for x in r.json()}

    # a consent makes that person's entry visible, the other stays hidden
    r = await api.post(
        base(c) + f"/players/{ids['Luca']}/consents",
        json={
            "kind": "analysis",
            "given_by": "self",
            "given_by_name": "Volljährig",
            "given_at": "2026-11-01T10:00:00+01:00",
        },
    )
    assert r.status_code == 201, r.text
    for who in staff:
        for url in (session, match):
            rows = await seen(who, url)
            assert ids["Luca"] in rows and ids["Noah"] not in rows
            assert rows[ids["Luca"]][0].startswith("Luca")
    r = await analyst.put(session, json={"records": [{"player_id": ids["Luca"], "status": "late"}]})
    assert r.status_code == 200, r.text

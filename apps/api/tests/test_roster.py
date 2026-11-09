from __future__ import annotations

import re
import uuid
from collections.abc import Callable
from datetime import timedelta
from typing import Any

import pytest

from handball_api.core.email import MemoryEmailSender
from handball_api.services.roster import today

from .conftest import Api, setup_club

pytestmark = pytest.mark.usefixtures("clean_db")


def roster_url(ids: dict[str, str]) -> str:
    return f"/v1/orgs/{ids['org']}/teams/{ids['team']}/seasons/{ids['season']}/roster"


async def test_roster_crud(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    url = roster_url(ids)
    r = await api.post(
        url,
        json={
            "first_name": "Lena",
            "last_name": "Meier",
            "jersey_number": 7,
            "main_position": "RA",
            "shooting_hand": "left",
        },
    )
    assert r.status_code == 201
    entry = r.json()
    assert entry["consent_complete"] is False
    dup = await api.post(url, json={"first_name": "Mia", "last_name": "Keller", "jersey_number": 7})
    assert dup.status_code == 409
    assert (
        await api.post(url, json={"first_name": "Mia", "last_name": "K", "jersey_number": 100})
    ).status_code == 422
    await api.post(url, json={"first_name": "Mia", "last_name": "Keller", "jersey_number": 9})
    base = f"/v1/orgs/{ids['org']}/teams/{ids['team']}/roster/{entry['id']}"
    upd = await api.patch(base, json={"jersey_number": 9})
    assert upd.status_code == 409
    upd = await api.patch(
        base, json={"jersey_number": 11, "secondary_positions": ["RR"], "last_name": "Meyer"}
    )
    assert upd.json()["jersey_number"] == 11
    assert upd.json()["last_name"] == "Meyer"
    roster = (await api.get(url)).json()
    assert [p["jersey_number"] for p in roster] == [9, 11]
    assert (await api.delete(base)).status_code == 204
    assert len((await api.get(url)).json()) == 1
    assert (await api.delete(base)).status_code == 404


CSV_OK = (
    "Vorname;Nachname;Nr;Position;Wurfhand;Jahrgang\n"
    "Lena;Meier;7;Rechtsaussen;links;2001\n"
    "Tim;Huber;12;TW;R;\n"
)


async def test_csv_import(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    url = roster_url(ids) + "/import"
    files = {"file": ("kader.csv", CSV_OK.encode("utf-8-sig"), "text/csv")}
    dry = (await api.post(url, files=files)).json()
    assert dry["dry_run"] is True
    assert dry["errors"] == []
    assert [r["main_position"] for r in dry["rows"]] == ["RA", "TW"]
    assert dry["rows"][0]["shooting_hand"] == "left"
    assert (await api.get(roster_url(ids))).json() == []
    done = (await api.post(url + "?dry_run=false", files=files)).json()
    assert done["created"] == 2
    assert len((await api.get(roster_url(ids))).json()) == 2
    # importing again collides with existing numbers
    again = (await api.post(url + "?dry_run=false", files=files)).json()
    assert again["created"] == 0
    assert {e["field"] for e in again["errors"]} == {"jersey_number"}


async def test_csv_import_errors(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    url = roster_url(ids) + "/import"
    bad = "first_name,last_name,number\nA,B,5\nC,D,5\n,E,6\nF,G,abc\n".encode("cp1252")
    res = (
        await api.post(url + "?dry_run=false", files={"file": ("k.csv", bad, "text/csv")})
    ).json()
    assert res["created"] == 0
    assert [(e["row"], e["field"]) for e in res["errors"]] == [
        (3, "jersey_number"),
        (4, "first_name"),
        (5, "jersey_number"),
    ]
    nohead = (await api.post(url, files={"file": ("k.csv", b"foo;bar\n1;2\n", "text/csv")})).json()
    assert "Vorname" in nohead["errors"][0]["message"]
    empty = (
        await api.post(url, files={"file": ("k.csv", b"Vorname;Nachname\n", "text/csv")})
    ).json()
    assert empty["errors"][0]["message"] == "The file contains no players"


async def test_consents(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api, youth=True)
    entry = (
        await api.post(
            roster_url(ids), json={"first_name": "Noah", "last_name": "Z", "birth_year": 2012}
        )
    ).json()
    base = f"/v1/orgs/{ids['org']}/teams/{ids['team']}/players/{entry['player_id']}/consents"
    body = {"given_by": "parent", "given_by_name": "Eva Z", "given_at": "2026-10-01T10:00:00+02:00"}
    assert (
        await api.post(base, json={**body, "kind": "analysis", "given_at": "2026-10-01T10:00:00"})
    ).status_code == 422
    # a minor cannot consent alone (addendum 01: parents decide for children)
    selfish = {**body, "given_by": "self", "kind": "analysis"}
    res = await api.post(base, json=selfish)
    assert res.status_code == 422
    assert res.json()["type"].endswith("parent-consent-required")
    await api.post(
        base, json={**body, "kind": "highlights_internal", "document_ref": "Formular 2026-14"}
    )
    assert (await api.get(roster_url(ids))).json()[0]["consent_complete"] is False
    c1 = (await api.post(base, json={**body, "kind": "analysis"})).json()
    assert (await api.get(roster_url(ids))).json()[0]["consent_complete"] is True
    assert len((await api.get(base)).json()) == 2
    revoked = (await api.delete(f"{base}/{c1['id']}")).json()
    assert revoked["revoked_at"] is not None
    assert (await api.get(roster_url(ids))).json()[0]["consent_complete"] is False


async def _join(
    make_api: Callable[[], Api],
    coach: Api,
    ids: dict[str, str],
    outbox: MemoryEmailSender,
    email: str,
    role: str = "player",
    player_id: str | None = None,
) -> Api:
    body = {"email": email, "team_id": ids["team"], "team_role": role}
    if player_id:
        body["player_id"] = player_id
    assert (await coach.post(f"/v1/orgs/{ids['org']}/invitations", json=body)).status_code == 201
    token = re.search(r"/invite/([\w-]+)", outbox.outbox[-1].text)
    assert token
    api = make_api()
    assert (await api.register(email, invitation_token=token.group(1))).status_code == 201
    return api


async def test_player_status(
    make_api: Callable[[], Api], outbox: MemoryEmailSender, owner_conn: Any
) -> None:
    coach = make_api()
    ids = await setup_club(coach)
    url = roster_url(ids)
    team = f"/v1/orgs/{ids['org']}/teams/{ids['team']}"
    lena = (await coach.post(url, json={"first_name": "Lena", "last_name": "Muster"})).json()
    nora = (await coach.post(url, json={"first_name": "Nora", "last_name": "Beispiel"})).json()
    lena_api = await _join(
        make_api, coach, ids, outbox, "lena@hc-test.ch", player_id=lena["player_id"]
    )
    manager = await _join(make_api, coach, ids, outbox, "tm@hc-test.ch", "team_manager")
    athletic = await _join(make_api, coach, ids, outbox, "ac@hc-test.ch", "athletic_coach")
    until = (today() + timedelta(days=7)).isoformat()

    # nobody has a status: everyone is fit
    assert [e["status"] for e in (await coach.get(url)).json()] == [None, None]
    assert (await coach.get(f"{team}/player-statuses")).json() == []

    r = await coach.put(
        f"{team}/players/{lena['player_id']}/status",
        json={"kind": "injured", "until": until, "note": "  Rückkehr nach Absprache "},
    )
    assert r.status_code == 200, r.text
    assert r.json()["kind"] == "injured" and r.json()["until"] == until
    assert r.json()["note"] == "Rückkehr nach Absprache"
    # the team manager and assistant coaches set statuses too
    r = await manager.put(f"{team}/players/{nora['player_id']}/status", json={"kind": "absent"})
    assert r.status_code == 200 and r.json()["until"] is None and r.json()["note"] is None
    r = await athletic.put(f"{team}/players/{nora['player_id']}/status", json={"kind": "injured"})
    assert r.status_code == 200 and r.json()["kind"] == "injured"

    statuses = {e["player_id"]: e["status"] for e in (await coach.get(url)).json()}
    assert statuses[lena["player_id"]]["kind"] == "injured"
    assert statuses[nora["player_id"]]["kind"] == "injured"
    listed = (await athletic.get(f"{team}/player-statuses")).json()
    assert [s["player_id"] for s in listed] == [lena["player_id"], nora["player_id"]]

    # a player sees only their own status and cannot read the list or set one
    own = {e["player_id"]: e["status"] for e in (await lena_api.get(url)).json()}
    assert own[lena["player_id"]]["kind"] == "injured" and own[nora["player_id"]] is None
    assert (await lena_api.get(f"{team}/player-statuses")).status_code == 403
    r = await lena_api.put(f"{team}/players/{nora['player_id']}/status", json={"kind": "absent"})
    assert r.status_code == 403
    assert (await lena_api.delete(f"{team}/players/{lena['player_id']}/status")).status_code == 403

    # validation: past until-date, long note, unknown kind, player outside the team
    past = (today() - timedelta(days=1)).isoformat()
    bad = [
        {"kind": "absent", "until": past},
        {"kind": "absent", "note": "x" * 141},
        {"kind": "sick"},
    ]
    for body in bad:
        r = await coach.put(f"{team}/players/{nora['player_id']}/status", json=body)
        assert r.status_code == 422, body
    stranger = "00000000-0000-0000-0000-000000000003"
    r = await coach.put(f"{team}/players/{stranger}/status", json={"kind": "absent"})
    assert r.status_code == 404

    # a status past its until-date reads as fit
    await owner_conn.execute(
        "UPDATE player_statuses SET until = $1 WHERE player_id = $2",
        today() - timedelta(days=1),
        uuid.UUID(lena["player_id"]),
    )
    statuses = {e["player_id"]: e["status"] for e in (await coach.get(url)).json()}
    assert statuses[lena["player_id"]] is None
    listed = (await coach.get(f"{team}/player-statuses")).json()
    assert [s["player_id"] for s in listed] == [nora["player_id"]]
    assert all(e["status"] is None for e in (await lena_api.get(url)).json())

    # back to fit (twice: still fit)
    assert (await coach.delete(f"{team}/players/{nora['player_id']}/status")).status_code == 204
    assert (await coach.delete(f"{team}/players/{nora['player_id']}/status")).status_code == 204
    assert (await coach.get(f"{team}/player-statuses")).json() == []

    # another club sees nothing
    other = make_api()
    await setup_club(other, "other@hc-test.ch")
    assert (await other.get(f"{team}/player-statuses")).status_code == 404
    r = await other.put(f"{team}/players/{nora['player_id']}/status", json={"kind": "absent"})
    assert r.status_code == 404

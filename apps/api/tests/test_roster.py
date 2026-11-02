from __future__ import annotations

from collections.abc import Callable

import pytest

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
        await api.post(
            base, json={**body, "kind": "video_analysis", "given_at": "2026-10-01T10:00:00"}
        )
    ).status_code == 422
    c1 = (await api.post(base, json={**body, "kind": "video_analysis"})).json()
    assert (await api.get(roster_url(ids))).json()[0]["consent_complete"] is False
    await api.post(
        base, json={**body, "kind": "identification", "document_ref": "Formular 2026-14"}
    )
    assert (await api.get(roster_url(ids))).json()[0]["consent_complete"] is True
    assert len((await api.get(base)).json()) == 2
    revoked = (await api.delete(f"{base}/{c1['id']}")).json()
    assert revoked["revoked_at"] is not None
    assert (await api.get(roster_url(ids))).json()[0]["consent_complete"] is False

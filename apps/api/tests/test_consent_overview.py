"""The team's consent overview per purpose (who may be filmed, analysed or shared)."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

import pytest

from handball_api.core.email import MemoryEmailSender

from .conftest import Api, setup_club
from .test_roster import _join, roster_url

pytestmark = pytest.mark.usefixtures("clean_db")

GIVEN = {"given_by_name": "Eva Muster", "given_at": "2026-09-01T10:00:00+02:00"}


def _by_kind(player: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {p["kind"]: p for p in player["purposes"]}


async def test_consent_overview(
    make_api: Callable[[], Api], outbox: MemoryEmailSender, owner_conn: Any
) -> None:
    coach = make_api()
    ids = await setup_club(coach)
    team = f"/v1/orgs/{ids['org']}/teams/{ids['team']}"
    url = f"{team}/seasons/{ids['season']}/consents"
    add = roster_url(ids)
    lena = (
        await coach.post(
            add, json={"first_name": "Lena", "last_name": "Muster", "jersey_number": 7}
        )
    ).json()
    noah = (
        await coach.post(
            add,
            json={
                "first_name": "Noah",
                "last_name": "Beispiel",
                "jersey_number": 3,
                "birth_year": 2011,
            },
        )
    ).json()
    mia = (await coach.post(add, json={"first_name": "Mia", "last_name": "Probst"})).json()
    gone = (await coach.post(add, json={"first_name": "Tim", "last_name": "Weg"})).json()
    r = await coach.patch(f"{team}/roster/{gone['id']}", json={"active": False})
    assert r.status_code == 200

    def consents(p: dict[str, Any]) -> str:
        return f"{team}/players/{p['player_id']}/consents"

    # Lena (adult) consents herself; Noah (a minor) through his mother, who later revokes one
    for kind in ("analysis", "highlights_internal"):
        body = {**GIVEN, "kind": kind, "given_by": "self", "given_by_name": "Lena Muster"}
        assert (await coach.post(consents(lena), json=body)).status_code == 201
    body = {**GIVEN, "kind": "analysis", "given_by": "parent"}
    assert (await coach.post(consents(noah), json=body)).status_code == 201
    body = {**GIVEN, "kind": "highlights_internal", "given_by": "parent"}
    revoked = (await coach.post(consents(noah), json=body)).json()
    assert (await coach.delete(f"{consents(noah)}/{revoked['id']}")).status_code == 200

    data = (await coach.get(url)).json()
    assert data["is_youth"] is False
    # active entries only, by jersey number (without one last)
    players = data["players"]
    assert [p["first_name"] for p in players] == ["Noah", "Lena", "Mia"]
    by = {p["player_id"]: _by_kind(p) for p in players}
    lena_c = by[lena["player_id"]]
    assert lena_c["analysis"]["state"] == "granted"
    assert lena_c["analysis"]["given_by"] == "self"
    assert lena_c["analysis"]["since"].startswith("2026-09-01")
    assert lena_c["training_data"] == {
        "kind": "training_data",
        "state": "missing",
        "since": None,
        "given_by": None,
        "given_by_name": None,
        "consent_id": None,
        "applicable": True,
    }
    noah_c = by[noah["player_id"]]
    assert noah_c["analysis"]["given_by"] == "parent"
    assert noah_c["analysis"]["given_by_name"] == "Eva Muster"
    assert noah_c["highlights_internal"]["state"] == "refused"
    assert noah_c["highlights_internal"]["consent_id"] == revoked["id"]
    assert noah_c["highlights_internal"]["since"] is not None
    assert next(p for p in players if p["first_name"] == "Noah")["minor"] is True
    assert next(p for p in players if p["first_name"] == "Mia")["minor"] is None
    assert all(s == "missing" for s in [c["state"] for c in by[mia["player_id"]].values()])

    summary = {s["kind"]: s for s in data["summary"]}
    assert summary["analysis"] == {
        "kind": "analysis",
        "applicable": True,
        "players": 3,
        "granted": 2,
        "refused": 0,
        "missing": 1,
    }
    assert summary["highlights_internal"]["granted"] == 1
    assert summary["highlights_internal"]["refused"] == 1
    assert summary["public_profile"]["missing"] == 3

    # a renewed consent counts again
    body = {**GIVEN, "kind": "highlights_internal", "given_by": "parent"}
    body["given_at"] = "2026-10-01T10:00:00+02:00"
    assert (await coach.post(consents(noah), json=body)).status_code == 201
    noah_c = {p["player_id"]: _by_kind(p) for p in (await coach.get(url)).json()["players"]}[
        noah["player_id"]
    ]
    assert noah_c["highlights_internal"]["state"] == "granted"
    assert noah_c["highlights_internal"]["since"].startswith("2026-10-01")

    # who manages roster and consents reads it: coach, team manager; not analysts or players
    manager = await _join(make_api, coach, ids, outbox, "tm@hc-test.ch", "team_manager")
    analyst = await _join(make_api, coach, ids, outbox, "an@hc-test.ch", "analyst")
    player = await _join(
        make_api, coach, ids, outbox, "lena@hc-test.ch", player_id=lena["player_id"]
    )
    assert (await manager.get(url)).status_code == 200
    assert (await analyst.get(url)).status_code == 403
    assert (await player.get(url)).status_code == 403

    # an entry from the official data without account or consent: still listed for organisers
    await owner_conn.execute(
        "UPDATE roster_entries SET official_provider = 'handball_ch', official_player_id = 77 "
        "WHERE player_id = $1",
        uuid.UUID(mia["player_id"]),
    )
    assert len((await manager.get(url)).json()["players"]) == 3

    # unknown season, another club
    assert (await coach.get(f"{team}/seasons/{uuid.uuid4()}/consents")).status_code == 404
    other = make_api()
    await setup_club(other, "other@hc-test.ch")
    assert (await other.get(url)).status_code == 404


async def test_consent_overview_youth(make_api: Callable[[], Api]) -> None:
    coach = make_api()
    ids = await setup_club(coach, youth=True)
    await coach.post(roster_url(ids), json={"first_name": "Ella", "last_name": "Klein"})
    data = (
        await coach.get(
            f"/v1/orgs/{ids['org']}/teams/{ids['team']}/seasons/{ids['season']}/consents"
        )
    ).json()
    assert data["is_youth"] is True
    applicable = {s["kind"]: s["applicable"] for s in data["summary"]}
    # public purposes cannot be given in youth teams (4.9)
    assert applicable == {
        "analysis": True,
        "highlights_internal": True,
        "highlights_public": False,
        "public_profile": False,
        "training_data": True,
    }
    assert _by_kind(data["players"][0])["public_profile"]["applicable"] is False

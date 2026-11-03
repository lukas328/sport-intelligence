"""Parents and own consents (addendum 01: role parent, guardianships, consent per purpose)."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

import pytest

from handball_api.core.email import MemoryEmailSender

from .conftest import Api, setup_club

pytestmark = pytest.mark.usefixtures("clean_db")


async def _invite(
    coach: Api,
    outbox: MemoryEmailSender,
    make_api: Callable[[], Api],
    ids: dict[str, Any],
    body: dict[str, Any],
) -> Api:
    r = await coach.post(
        f"/v1/orgs/{ids['org']}/invitations", json={"team_id": ids["team"], **body}
    )
    assert r.status_code == 201, r.text
    token = re.search(r"/invite/([\w-]+)", outbox.outbox[-1].text)
    assert token
    api = make_api()
    reg = await api.register(body["email"], name="Eva Z", invitation_token=token.group(1))
    assert reg.status_code == 201, reg.text
    return api


async def test_parent_decides_for_own_child_only(
    make_api: Callable[[], Api], outbox: MemoryEmailSender
) -> None:
    coach = make_api()
    ids = await setup_club(coach, youth=True)
    roster = f"/v1/orgs/{ids['org']}/teams/{ids['team']}/seasons/{ids['season']}/roster"
    noah = (
        await coach.post(roster, json={"first_name": "Noah", "last_name": "Z", "birth_year": 2013})
    ).json()
    mia = (
        await coach.post(roster, json={"first_name": "Mia", "last_name": "Y", "birth_year": 2013})
    ).json()

    bad = await coach.post(
        f"/v1/orgs/{ids['org']}/invitations",
        json={"email": "p@hc-test.ch", "team_id": ids["team"], "team_role": "parent"},
    )
    assert bad.status_code == 422
    parent = await _invite(
        coach,
        outbox,
        make_api,
        ids,
        {"email": "eva@hc-test.ch", "team_role": "parent", "player_id": noah["player_id"]},
    )
    base = f"/v1/orgs/{ids['org']}/me/consents"
    subjects = (await parent.get(base)).json()
    assert [(s["first_name"], s["relation"], s["minor"]) for s in subjects] == [
        ("Noah", "guardian", True)
    ]
    assert subjects[0]["teams"][0]["is_youth"] is True
    # parents see their child, not the team
    assert (await parent.get(f"/v1/orgs/{ids['org']}/teams/{ids['team']}")).status_code in (
        403,
        404,
    )
    assert (await parent.get(roster)).status_code in (403, 404)

    r = await parent.post(f"{base}/{noah['player_id']}", json={"kind": "analysis"})
    assert r.status_code == 201
    assert r.json()["given_by"] == "parent" and r.json()["given_by_name"] == "Eva Z"
    public = await parent.post(f"{base}/{noah['player_id']}", json={"kind": "public_profile"})
    assert public.status_code == 403 and public.json()["type"].endswith("youth-protection")
    again = await parent.post(f"{base}/{noah['player_id']}", json={"kind": "analysis"})
    assert again.json()["id"] == r.json()["id"]
    assert (
        await parent.post(f"{base}/{mia['player_id']}", json={"kind": "analysis"})
    ).status_code == 404

    entries = {e["first_name"]: e for e in (await coach.get(roster)).json()}
    assert entries["Noah"]["consent_complete"] is True
    assert entries["Mia"]["consent_complete"] is False

    export = (await parent.get("/v1/me/export")).json()
    assert [c["first_name"] for c in export["children"]] == ["Noah"]

    assert (await parent.delete(f"{base}/{noah['player_id']}/analysis")).status_code == 204
    after = (await parent.get(base)).json()[0]
    assert after["active"] == []
    assert len(after["history"]) == 1 and after["history"][0]["revoked_at"] is not None
    entries = {e["first_name"]: e for e in (await coach.get(roster)).json()}
    assert entries["Noah"]["consent_complete"] is False


async def test_adult_player_consents_for_self(
    make_api: Callable[[], Api], outbox: MemoryEmailSender
) -> None:
    coach = make_api()
    ids = await setup_club(coach)
    roster = f"/v1/orgs/{ids['org']}/teams/{ids['team']}/seasons/{ids['season']}/roster"
    lena = (
        await coach.post(roster, json={"first_name": "Lena", "last_name": "M", "birth_year": 1998})
    ).json()
    player = await _invite(
        coach,
        outbox,
        make_api,
        ids,
        {"email": "lena@hc-test.ch", "team_role": "player", "player_id": lena["player_id"]},
    )
    base = f"/v1/orgs/{ids['org']}/me/consents"
    subjects = (await player.get(base)).json()
    assert [(s["relation"], s["minor"]) for s in subjects] == [("self", False)]
    for kind in ("analysis", "highlights_internal"):
        r = await player.post(f"{base}/{lena['player_id']}", json={"kind": kind})
        assert r.status_code == 201 and r.json()["given_by"] == "self"
    assert sorted((await player.get(base)).json()[0]["active"]) == [
        "analysis",
        "highlights_internal",
    ]
    assert (await coach.get(base)).json() == []


async def test_minor_player_cannot_consent_alone(
    make_api: Callable[[], Api], outbox: MemoryEmailSender
) -> None:
    coach = make_api()
    ids = await setup_club(coach, youth=True)
    roster = f"/v1/orgs/{ids['org']}/teams/{ids['team']}/seasons/{ids['season']}/roster"
    kid = (
        await coach.post(roster, json={"first_name": "Ben", "last_name": "K", "birth_year": 2012})
    ).json()
    player = await _invite(
        coach,
        outbox,
        make_api,
        ids,
        {"email": "ben@hc-test.ch", "team_role": "player", "player_id": kid["player_id"]},
    )
    r = await player.post(
        f"/v1/orgs/{ids['org']}/me/consents/{kid['player_id']}", json={"kind": "analysis"}
    )
    assert r.status_code == 422
    assert r.json()["type"].endswith("parent-consent-required")


async def test_admin_handover(make_api: Callable[[], Api], outbox: MemoryEmailSender) -> None:
    admin = make_api()
    ids = await setup_club(admin)
    coach = await _invite(
        admin, outbox, make_api, ids, {"email": "c@hc-test.ch", "team_role": "coach"}
    )
    members = f"/v1/orgs/{ids['org']}/members"
    me = admin.user["id"]
    other = coach.user["id"]
    # the only admin cannot step down; a coach cannot promote anyone
    assert (await admin.patch(f"{members}/{me}", json={"org_role": "member"})).status_code == 409
    assert (
        await coach.patch(f"{members}/{other}", json={"org_role": "org_admin"})
    ).status_code == 403
    r = await admin.patch(f"{members}/{other}", json={"org_role": "org_admin"})
    assert r.status_code == 200 and r.json() == {"org_role": "org_admin"}
    assert (await admin.patch(f"{members}/{me}", json={"org_role": "member"})).status_code == 200
    roles = {m["user_id"]: m["org_role"] for m in (await coach.get(members)).json()}
    assert roles == {me: "member", other: "org_admin"}
    assert (await admin.get(members)).status_code == 403

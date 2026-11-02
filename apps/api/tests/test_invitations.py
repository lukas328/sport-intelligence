from __future__ import annotations

import re
from collections.abc import Callable

import pytest

from handball_api.core.email import MemoryEmailSender

from .conftest import Api, setup_club

pytestmark = pytest.mark.usefixtures("clean_db")


def token_from(outbox: MemoryEmailSender) -> str:
    m = re.search(r"/invite/([\w-]+)", outbox.outbox[-1].text)
    assert m
    return m.group(1)


async def test_invite_player_new_account(
    make_api: Callable[[], Api], outbox: MemoryEmailSender
) -> None:
    coach = make_api()
    ids = await setup_club(coach)
    entry = (
        await coach.post(
            f"/v1/orgs/{ids['org']}/teams/{ids['team']}/seasons/{ids['season']}/roster",
            json={"first_name": "Lena", "last_name": "M", "jersey_number": 7},
        )
    ).json()
    r = await coach.post(
        f"/v1/orgs/{ids['org']}/invitations",
        json={
            "email": "lena@hc-test.ch",
            "team_id": ids["team"],
            "team_role": "player",
            "player_id": entry["player_id"],
        },
    )
    assert r.status_code == 201
    mail = outbox.outbox[-1]
    assert mail.to == "lena@hc-test.ch"
    assert mail.subject == "Einladung zu HC Test"
    token = token_from(outbox)

    guest = make_api()
    preview = (await guest.get(f"/v1/invitations/{token}")).json()
    assert preview == {
        "organization_name": "HC Test",
        "team_name": "Herren 1",
        "email": "lena@hc-test.ch",
        "org_role": "member",
        "team_role": "player",
        "status": "pending",
        "account_exists": False,
    }
    assert (await guest.register("lena@hc-test.ch", invitation_token=token)).status_code == 201
    assert guest.user["organizations"][0]["role"] == "member"
    teams = (await guest.get(f"/v1/orgs/{ids['org']}/teams")).json()
    assert teams[0]["my_role"] == "player"
    roster = (
        await coach.get(f"/v1/orgs/{ids['org']}/teams/{ids['team']}/seasons/{ids['season']}/roster")
    ).json()
    assert roster[0]["has_account"] is True
    assert (await guest.get(f"/v1/invitations/{token}")).json()["status"] == "accepted"
    assert (await guest.post(f"/v1/invitations/{token}/accept")).status_code == 410


async def test_invite_existing_account_and_mismatch(
    make_api: Callable[[], Api], outbox: MemoryEmailSender
) -> None:
    admin = make_api()
    ids = await setup_club(admin)
    other = make_api()
    await other.register("other@hc-test.ch")
    await admin.post(
        f"/v1/orgs/{ids['org']}/invitations",
        json={"email": "anna@hc-test.ch", "org_role": "org_admin"},
    )
    token = token_from(outbox)
    assert (await other.get(f"/v1/invitations/{token}")).json()["account_exists"] is False
    mismatch = await other.post(f"/v1/invitations/{token}/accept")
    assert mismatch.status_code == 403
    anna = make_api()
    await anna.register("anna@hc-test.ch")
    assert (await anna.post(f"/v1/invitations/{token}/accept")).json() == {
        "organization_id": ids["org"]
    }
    assert (await anna.get(f"/v1/orgs/{ids['org']}")).json()["my_role"] == "org_admin"


async def test_revoke_and_list(make_api: Callable[[], Api], outbox: MemoryEmailSender) -> None:
    admin = make_api()
    ids = await setup_club(admin)
    inv = (
        await admin.post(
            f"/v1/orgs/{ids['org']}/invitations",
            json={"email": "x@hc-test.ch", "team_id": ids["team"], "team_role": "analyst"},
        )
    ).json()
    token = token_from(outbox)
    assert len((await admin.get(f"/v1/orgs/{ids['org']}/invitations")).json()) == 1
    assert (
        len((await admin.get(f"/v1/orgs/{ids['org']}/invitations?team_id={ids['team']}")).json())
        == 1
    )
    assert (await admin.delete(f"/v1/orgs/{ids['org']}/invitations/{inv['id']}")).json()[
        "revoked_at"
    ]
    x = make_api()
    await x.register("x@hc-test.ch")
    r = await x.post(f"/v1/invitations/{token}/accept")
    assert r.status_code == 410
    assert r.json()["type"].endswith(":invitation-revoked")
    assert (await x.get("/v1/invitations/not-a-real-token-123")).status_code == 404


async def test_invitation_validation(make_api: Callable[[], Api]) -> None:
    admin = make_api()
    ids = await setup_club(admin)
    url = f"/v1/orgs/{ids['org']}/invitations"
    assert (
        await admin.post(url, json={"email": "a@hc-test.ch"})
    ).status_code == 422  # member without team
    assert (
        await admin.post(url, json={"email": "a@hc-test.ch", "team_id": ids["team"]})
    ).status_code == 422
    r = await admin.post(
        url, json={"email": "a@hc-test.ch", "org_role": "org_admin", "player_id": ids["team"]}
    )
    assert r.status_code == 422


async def test_team_member_management(
    make_api: Callable[[], Api], outbox: MemoryEmailSender
) -> None:
    coach = make_api()
    ids = await setup_club(coach)
    await coach.post(
        f"/v1/orgs/{ids['org']}/invitations",
        json={"email": "p@hc-test.ch", "team_id": ids["team"], "team_role": "player"},
    )
    p = make_api()
    await p.register("p@hc-test.ch", invitation_token=token_from(outbox))
    base = f"/v1/orgs/{ids['org']}/teams/{ids['team']}/members"
    members = (await coach.get(base)).json()
    assert sorted(m["role"] for m in members) == ["coach", "player"]
    pid = p.user["id"]
    assert (await coach.patch(f"{base}/{pid}", json={"role": "goalkeeper"})).json()[
        "role"
    ] == "goalkeeper"
    assert (await coach.delete(f"{base}/{pid}")).status_code == 204
    assert (await coach.delete(f"{base}/{pid}")).status_code == 404

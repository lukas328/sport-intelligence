"""Federation and volume licences (addendum 01, 5.10)."""

from __future__ import annotations

import re
from collections.abc import Callable

import asyncpg
import pytest

from handball_api.core.email import MemoryEmailSender

from .conftest import Api, setup_club
from .test_matches import new_match
from .test_ops import operators  # noqa: F401 (fixture)

pytestmark = pytest.mark.usefixtures("clean_db", "operators")


def token_of(outbox: MemoryEmailSender) -> str:
    m = re.search(r"/federation/join\?token=([\w-]+)", outbox.outbox[-1].text)
    assert m, outbox.outbox[-1].text
    return m.group(1)


async def test_federation_licences(
    make_api: Callable[[], Api], outbox: MemoryEmailSender, owner_conn: asyncpg.Connection
) -> None:
    op = make_api()
    assert (await op.register("ops@handball-ops.ch", name="Ops")).status_code == 201
    fed_admin = make_api()
    assert (await fed_admin.register("leitung@verband.ch", name="Verband")).status_code == 201

    body = {
        "name": "Regionalverband Mitte",
        "plan": "club",
        "seat_quota": 2,
        "contract_until": "2027-06-30",
        "billing_address": {"street": "Hallenweg 1", "pcode": "3000", "city": "Bern"},
    }
    fed = (await op.post("/v1/ops/federations", json=body)).json()
    assert fed["plan"] == "club" and fed["seat_quota"] == 2
    assert (await fed_admin.post("/v1/ops/federations", json=body)).status_code == 404
    r = await op.post(
        f"/v1/ops/federations/{fed['id']}/admins", json={"email": "leitung@verband.ch"}
    )
    assert r.status_code == 204
    assert [f["name"] for f in (await fed_admin.get("/v1/federations")).json()] == [body["name"]]

    # a club is invited, its admin accepts: the club now runs on the federation's plan
    club = make_api()
    ids = await setup_club(club)
    org = ids["org"]
    url = f"/v1/federations/{fed['id']}"
    assert (
        await fed_admin.post(f"{url}/invites", json={"email": "coach@hc-test.ch"})
    ).status_code == 201
    token = token_of(outbox)
    joined = await club.post(f"/v1/orgs/{org}/federation/join", json={"token": token})
    assert joined.status_code == 200, joined.text
    billing = (await club.get(f"/v1/orgs/{org}/billing")).json()
    assert billing["plan"] == "club"
    status = (await club.get(f"/v1/orgs/{org}/federation")).json()
    assert status["federation"] == body["name"] and status["contract_until"] == "2027-06-30"
    # the link works once; a second club admin cannot reuse it
    again = await club.post(f"/v1/orgs/{org}/federation/join", json={"token": token})
    assert again.status_code == 404

    # quota: one more invitation, then full
    assert (await fed_admin.post(f"{url}/invites", json={"email": "b@club.ch"})).status_code == 201
    full = await fed_admin.post(f"{url}/invites", json={"email": "c@club.ch"})
    assert full.status_code == 409 and full.json()["type"].endswith("quota-reached")

    # overview: usage per club, no aggregates below five clubs, no club content
    m = await new_match(club, ids)
    await club.post(
        f"/v1/orgs/{org}/matches/{m['id']}/events",
        json={"type": "shot", "side": "own", "outcome": "goal"},
    )
    ov = (await fed_admin.get(url)).json()
    assert ov["seats_used"] == 1 and ov["open_invites"] == 1
    member = ov["members"][0]
    assert (member["name"], member["teams"], member["matches"], member["members"]) == (
        "HC Test",
        1,
        1,
        1,
    )
    assert ov["aggregate"] == {"clubs_with_data": 1, "min_clubs": 5}
    assert "events" not in str(ov) and "video" not in str(ov)
    assert (await club.get(url)).status_code == 404  # only federation admins

    pdf = await op.get(f"/v1/ops/federations/{fed['id']}/invoice?lang=fr")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")

    # leaving ends the licence; the club falls back to Free
    assert (await club.delete(f"/v1/orgs/{org}/federation")).status_code == 204
    assert (await club.get(f"/v1/orgs/{org}/billing")).json()["plan"] == "free"
    assert (await club.get(f"/v1/orgs/{org}/federation")).json() is None
    assert (await op.get(f"/v1/ops/federations/{fed['id']}/invoice")).status_code == 409


async def test_aggregates_from_five_clubs(
    make_api: Callable[[], Api], outbox: MemoryEmailSender
) -> None:
    op = make_api()
    await op.register("ops@handball-ops.ch", name="Ops")
    fed = (
        await op.post(
            "/v1/ops/federations", json={"name": "Verband Fünf", "plan": "team", "seat_quota": 5}
        )
    ).json()
    await op.post(f"/v1/ops/federations/{fed['id']}/admins", json={"email": "ops@handball-ops.ch"})
    url = f"/v1/federations/{fed['id']}"
    for i in range(5):
        club = make_api()
        email = f"coach{i}@club{i}.ch"
        ids = await setup_club(club, email=email)
        assert (await op.post(f"{url}/invites", json={"email": email})).status_code == 201
        r = await club.post(
            f"/v1/orgs/{ids['org']}/federation/join", json={"token": token_of(outbox)}
        )
        assert r.status_code == 200
        m = await new_match(club, ids)
        for outcome in ("goal", "goal", "miss") if i % 2 else ("goal", "save"):
            await club.post(
                f"/v1/orgs/{ids['org']}/matches/{m['id']}/events",
                json={"type": "shot", "side": "own", "outcome": outcome},
            )
    agg = (await op.get(url)).json()["aggregate"]
    # 5 matches; goals 2+2+2+... : clubs 0,2,4 score 1 of 2, clubs 1,3 score 2 of 3
    assert agg["clubs_with_data"] == 5 and agg["matches_with_events"] == 5
    assert agg["goals_per_match"] == round(7 / 5, 1) and agg["shooting_pct"] == round(7 / 12, 3)

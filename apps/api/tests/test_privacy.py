"""Personal data export, account and club deletion (M9)."""

from __future__ import annotations

import json
from collections.abc import Callable

import pytest

from handball_api.core.email import MemoryEmailSender
from handball_api.core.storage import MemoryStorage

from .conftest import Api, setup_club
from .test_matches import new_match, upload
from .test_training import add_member

pytestmark = pytest.mark.usefixtures("clean_db")


async def test_export_and_account_deletion(
    make_api: Callable[[], Api], outbox: MemoryEmailSender
) -> None:
    coach = make_api()
    ids = await setup_club(coach)
    org = ids["org"]
    m = await new_match(coach, ids)
    mia = await add_member(make_api, coach, ids, outbox, "mia@hc-test.ch")
    await mia.post(
        f"/v1/orgs/{org}/matches/{m['id']}/comments", json={"t_ms": 5, "body": "Gute Abwehr"}
    )

    r = await mia.get("/v1/me/export")
    assert r.status_code == 200
    assert "attachment" in r.headers["content-disposition"]
    data = json.loads(r.content)
    assert data["account"]["email"] == "mia@hc-test.ch"
    assert data["organizations"][0]["role"] == "member"
    assert data["teams"][0]["role"] == "player"
    assert data["comments"][0]["body"] == "Gute Abwehr"
    assert data["sessions"] and "password" not in r.text.lower().replace("password_reset", "")

    # wrong confirmation or password
    assert (
        await mia.post("/v1/me/delete", json={"confirm_email": "x@y.ch", "password": "x"})
    ).status_code == 422
    assert (
        await mia.post(
            "/v1/me/delete", json={"confirm_email": "mia@hc-test.ch", "password": "wrong"}
        )
    ).status_code == 403
    # the only admin of a club with members cannot leave it orphaned
    r = await coach.post(
        "/v1/me/delete", json={"confirm_email": "coach@hc-test.ch", "password": "correct-horse-1"}
    )
    assert r.status_code == 409 and r.json()["type"].endswith("last-admin")

    r = await mia.post(
        "/v1/me/delete", json={"confirm_email": "mia@hc-test.ch", "password": "correct-horse-1"}
    )
    assert r.status_code == 204
    assert (await mia.get("/v1/me")).status_code == 401
    comments = (await coach.get(f"/v1/orgs/{org}/matches/{m['id']}/comments")).json()
    assert comments[0]["body"] == "Gute Abwehr" and not comments[0]["author_name"]
    members = (await coach.get(f"/v1/orgs/{org}/members")).json()
    assert all(x["email"] != "mia@hc-test.ch" for x in members)

    # alone in the club now: deleting the account deletes the club as well
    r = await coach.post(
        "/v1/me/delete", json={"confirm_email": "coach@hc-test.ch", "password": "correct-horse-1"}
    )
    assert r.status_code == 204


async def test_club_deletion(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    m = await new_match(api, ids)
    await upload(api, ids, m["id"], b"v" * 100)
    storage: MemoryStorage = api.app.state.storage
    await storage.put(
        "artifacts", f"{org}/x/analysis/chunk_00000.bin", b"1", "application/octet-stream"
    )
    await storage.put("artifacts", "other-org/keep.bin", b"1", "application/octet-stream")
    url = f"/v1/orgs/{org}/delete"
    assert (await api.post(url, json={"confirm_name": "HC Falsch"})).status_code == 422
    assert (await api.post(url, json={"confirm_name": "HC Test"})).status_code == 204
    assert (await api.get(f"/v1/orgs/{org}")).status_code == 404
    assert not [k for k in storage.objects if k[1].startswith(f"{org}/")]
    assert ("artifacts", "other-org/keep.bin") in storage.objects
    assert (await api.get("/v1/me")).status_code == 200  # the account stays

from __future__ import annotations

import re
from collections.abc import Callable

import pytest

from handball_api.core.email import MemoryEmailSender

from .conftest import Api

pytestmark = pytest.mark.usefixtures("clean_db")


def link(outbox: MemoryEmailSender, path: str) -> str:
    m = re.search(rf"{path}\?token=([\w-]+)", outbox.outbox[-1].text)
    assert m, outbox.outbox[-1].text
    return m.group(1)


async def test_password_reset(make_api: Callable[[], Api], outbox: MemoryEmailSender) -> None:
    a, b = make_api(), make_api()
    await a.register("r@hc-test.ch", name="Rita")
    await b.post("/v1/auth/login", json={"email": "r@hc-test.ch", "password": "correct-horse-1"})
    n = len(outbox.outbox)
    assert (
        await b.post("/v1/auth/password/forgot", json={"email": "nobody@hc-test.ch"})
    ).status_code == 202
    assert len(outbox.outbox) == n
    assert (
        await b.post("/v1/auth/password/forgot", json={"email": "r@hc-test.ch"})
    ).status_code == 202
    assert outbox.outbox[-1].subject == "Passwort zurücksetzen"
    token = link(outbox, "/auth/reset")
    weak = await b.post("/v1/auth/password/reset", json={"token": token, "password": "short"})
    assert weak.status_code == 422
    c = make_api()
    await c.post("/v1/auth/password/forgot", json={"email": "r@hc-test.ch"})
    token = link(outbox, "/auth/reset")
    ok = await c.post(
        "/v1/auth/password/reset", json={"token": token, "password": "brand-new-pass-2"}
    )
    assert ok.json() == {"status": "ok"}
    assert (await c.get("/v1/me")).status_code == 200
    # all earlier sessions are revoked
    assert (await a.get("/v1/me")).status_code == 401
    assert (await b.get("/v1/me")).status_code == 401
    again = await make_api().post(
        "/v1/auth/password/reset", json={"token": token, "password": "brand-new-pass-3"}
    )
    assert again.status_code == 400
    login = await make_api().post(
        "/v1/auth/login", json={"email": "r@hc-test.ch", "password": "brand-new-pass-2"}
    )
    assert login.json() == {"status": "ok"}


async def test_failed_reset_rolls_back_token(
    make_api: Callable[[], Api], outbox: MemoryEmailSender
) -> None:
    api = make_api()
    await api.register("w@hc-test.ch")
    await api.post("/v1/auth/password/forgot", json={"email": "w@hc-test.ch"})
    token = link(outbox, "/auth/reset")
    assert (
        await api.post("/v1/auth/password/reset", json={"token": token, "password": "x"})
    ).status_code == 422
    # the transaction rolled back, so the link still works with a valid password
    ok = await api.post(
        "/v1/auth/password/reset", json={"token": token, "password": "long-enough-pass"}
    )
    assert ok.status_code == 200


async def test_email_verification(make_api: Callable[[], Api], outbox: MemoryEmailSender) -> None:
    api = make_api()
    await api.register("v@hc-test.ch")
    assert outbox.outbox[-1].subject == "Bitte bestätige deine E-Mail-Adresse"
    assert (await api.get("/v1/me")).json()["email_verified"] is False
    token = link(outbox, "/auth/verify")
    assert (
        await make_api().post("/v1/auth/email/verify", json={"token": token})
    ).status_code == 204
    assert (await api.get("/v1/me")).json()["email_verified"] is True
    n = len(outbox.outbox)
    assert (await api.post("/v1/me/email/verify")).status_code == 202
    assert len(outbox.outbox) == n  # already verified, nothing sent


async def test_change_password_and_sessions(make_api: Callable[[], Api]) -> None:
    a, b = make_api(), make_api()
    await a.register("s@hc-test.ch")
    await b.post(
        "/v1/auth/login",
        json={"email": "s@hc-test.ch", "password": "correct-horse-1"},
        headers={"user-agent": "Tablet"},
    )
    sessions = (await a.get("/v1/me/sessions")).json()
    assert len(sessions) == 2
    assert sum(s["current"] for s in sessions) == 1
    assert {s["method"] for s in sessions} == {"password"}
    other = next(s for s in sessions if not s["current"])
    assert other["user_agent"] == "Tablet"
    assert (await a.delete(f"/v1/me/sessions/{other['id']}")).status_code == 204
    assert (await b.get("/v1/me")).status_code == 401
    assert (await a.delete(f"/v1/me/sessions/{other['id']}")).status_code == 404

    await b.post("/v1/auth/login", json={"email": "s@hc-test.ch", "password": "correct-horse-1"})
    bad = await a.post(
        "/v1/me/password", json={"current_password": "wrong", "new_password": "another-pass-9"}
    )
    assert bad.status_code == 403
    ok = await a.post(
        "/v1/me/password",
        json={"current_password": "correct-horse-1", "new_password": "another-pass-9"},
    )
    assert ok.status_code == 204
    assert (await b.get("/v1/me")).status_code == 401  # other sessions signed out
    assert (await a.get("/v1/me")).status_code == 200

    await b.post("/v1/auth/login", json={"email": "s@hc-test.ch", "password": "another-pass-9"})
    assert (await a.post("/v1/me/sessions/revoke-others")).status_code == 204
    assert (await b.get("/v1/me")).status_code == 401
    me = (await a.get("/v1/me")).json()
    assert me["has_password"] is True
    assert me["linked_providers"] == []

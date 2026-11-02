from __future__ import annotations

import re
from collections.abc import Callable

import pyotp
import pytest

from handball_api.core.email import MemoryEmailSender

from .conftest import Api

pytestmark = pytest.mark.usefixtures("clean_db")


async def test_register_me_logout_login(make_api: Callable[[], Api]) -> None:
    api = make_api()
    r = await api.register("Anna@HC-Test.ch", name="Anna")
    assert r.status_code == 201
    assert r.json() == {"status": "ok"}
    assert "httponly" in r.headers.get_list("set-cookie")[0].lower()
    me = (await api.get("/v1/me")).json()
    assert me["email"] == "Anna@hc-test.ch"  # domain normalised
    assert me["organizations"] == []

    assert (await api.post("/v1/auth/logout")).status_code == 204
    assert (await api.get("/v1/me")).status_code == 401

    bad = await api.post(
        "/v1/auth/login", json={"email": "anna@hc-test.ch", "password": "nope-nope-nope"}
    )
    assert bad.status_code == 401
    assert bad.json()["type"].endswith(":invalid-credentials")
    ok = await api.post(
        "/v1/auth/login", json={"email": "anna@hc-test.ch", "password": "correct-horse-1"}
    )
    assert ok.json() == {"status": "ok"}
    assert (await api.get("/v1/me")).status_code == 200


async def test_register_validation(make_api: Callable[[], Api]) -> None:
    api = make_api()
    weak = await api.register("b@hc-test.ch", password="short")
    assert weak.status_code == 422
    assert weak.json()["type"].endswith(":weak-password")
    r = await api.post(
        "/v1/auth/register",
        json={
            "email": "b@hc-test.ch",
            "name": "B",
            "password": "correct-horse-1",
            "accept_terms": False,
        },
    )
    assert r.json()["type"].endswith(":terms-not-accepted")
    assert (await api.register("b@hc-test.ch")).status_code == 201
    dup = await make_api().register("B@hc-test.ch")
    assert dup.status_code == 409


async def test_unknown_user_login_is_generic(make_api: Callable[[], Api]) -> None:
    r = await make_api().post(
        "/v1/auth/login", json={"email": "ghost@hc-test.ch", "password": "whatever-123"}
    )
    assert r.status_code == 401
    assert r.json()["type"].endswith(":invalid-credentials")


async def test_csrf_required_with_session(make_api: Callable[[], Api]) -> None:
    api = make_api()
    await api.register("c@hc-test.ch")
    r = await api.http.post("/v1/orgs", json={"name": "X"})  # no CSRF header
    assert r.status_code == 403
    assert r.json()["type"].endswith(":csrf-failed")
    r = await api.post("/v1/orgs", json={"name": "X"}, headers={"x-csrf-token": "forged"})
    assert r.status_code == 403


async def test_foreign_origin_rejected(make_api: Callable[[], Api]) -> None:
    api = make_api()
    r = await api.post(
        "/v1/auth/login",
        json={"email": "a@hc-test.ch", "password": "x"},
        headers={"origin": "https://evil.test"},
    )
    assert r.status_code == 403
    assert r.json()["type"].endswith(":origin-not-allowed")


async def test_magic_link(make_api: Callable[[], Api], outbox: MemoryEmailSender) -> None:
    api = make_api()
    await api.register("m@hc-test.ch", name="Mia")
    await api.post("/v1/auth/logout")
    assert (
        await api.post("/v1/auth/magic-link", json={"email": "nobody@hc-test.ch"})
    ).status_code == 202
    assert outbox.outbox == []
    assert (
        await api.post("/v1/auth/magic-link", json={"email": "m@hc-test.ch"})
    ).status_code == 202
    mail = outbox.outbox[-1]
    assert mail.subject == "Dein Anmeldelink"
    assert "Hallo Mia" in mail.text
    token = re.search(r"token=([\w-]+)", mail.text)
    assert token
    r = await api.post("/v1/auth/magic-link/consume", json={"token": token.group(1)})
    assert r.json() == {"status": "ok"}
    assert (await api.get("/v1/me")).status_code == 200
    again = await make_api().post("/v1/auth/magic-link/consume", json={"token": token.group(1)})
    assert again.status_code == 400


async def test_totp_flow(make_api: Callable[[], Api]) -> None:
    api = make_api()
    await api.register("t@hc-test.ch")
    setup = (await api.post("/v1/me/totp/setup")).json()
    assert setup["otpauth_uri"].startswith("otpauth://totp/")
    totp = pyotp.TOTP(setup["secret"])
    assert (await api.post("/v1/me/totp/enable", json={"code": "000000"})).status_code == 422
    assert (await api.post("/v1/me/totp/enable", json={"code": totp.now()})).status_code == 204
    assert (await api.get("/v1/me")).json()["totp_enabled"] is True
    assert (await api.post("/v1/me/totp/setup")).status_code == 409

    await api.post("/v1/auth/logout")
    r = await api.post(
        "/v1/auth/login", json={"email": "t@hc-test.ch", "password": "correct-horse-1"}
    )
    assert r.json() == {"status": "totp_required"}
    me = await api.get("/v1/me")
    assert me.status_code == 401
    assert me.json()["type"].endswith(":totp-required")
    assert (await api.post("/v1/auth/login/totp", json={"code": "123456"})).status_code == 401
    assert (await api.post("/v1/auth/login/totp", json={"code": totp.now()})).json() == {
        "status": "ok"
    }
    assert (await api.get("/v1/me")).status_code == 200
    assert (await api.post("/v1/auth/login/totp", json={"code": totp.now()})).status_code == 409

    assert (await api.post("/v1/me/totp/disable", json={"code": "111111"})).status_code == 422
    assert (await api.post("/v1/me/totp/disable", json={"code": totp.now()})).status_code == 204
    assert (await api.post("/v1/me/totp/disable", json={"code": totp.now()})).status_code == 409


async def test_update_me(make_api: Callable[[], Api]) -> None:
    api = make_api()
    await api.register("u@hc-test.ch")
    r = await api.patch("/v1/me", json={"name": "Neu", "locale": "fr"})
    assert r.json()["name"] == "Neu"
    assert r.json()["locale"] == "fr"


async def test_rate_limit(make_api: Callable[[], Api]) -> None:
    api = make_api()
    codes = [
        (
            await api.post(
                "/v1/auth/login", json={"email": "x@hc-test.ch", "password": "wrong-pass-1"}
            )
        ).status_code
        for _ in range(11)
    ]
    assert codes[:10] == [401] * 10
    assert codes[10] == 429

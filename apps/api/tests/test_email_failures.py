"""A failing mail provider must not turn a successful action into a 500."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from structlog.testing import capture_logs

from handball_api.core.db import enable_system_access, open_session
from handball_api.core.email import Email, MemoryEmailSender, try_send
from handball_api.services import support
from handball_api.services.context import Ctx

from .conftest import Api, setup_club

pytestmark = pytest.mark.usefixtures("clean_db")


class MailDownError(Exception):
    def __str__(self) -> str:  # providers echo the recipient: it must not reach the log
        return "550 mailbox <secret-addr@hc-test.ch> unavailable"


@pytest.fixture
def mail_down(outbox: MemoryEmailSender, monkeypatch: pytest.MonkeyPatch) -> Callable[[], None]:
    async def broken(email: Email) -> None:
        raise MailDownError

    def down() -> None:
        monkeypatch.setattr(outbox, "send", broken)

    return down


async def test_try_send_logs_without_address() -> None:
    class Broken:
        async def send(self, email: Email) -> None:
            raise MailDownError

    with capture_logs() as logs:
        ok = await try_send(Broken(), Email("secret-addr@hc-test.ch", "s", "t"), "x", user_id="1")
    assert ok is False
    assert logs == [
        {
            "event": "email_send_failed",
            "purpose": "x",
            "error": "MailDownError",
            "user_id": "1",
            "log_level": "error",
        }
    ]
    assert "secret-addr" not in repr(logs)


async def test_register_survives_and_verification_can_be_resent(
    make_api: Callable[[], Api],
    outbox: MemoryEmailSender,
    mail_down: Callable[[], None],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mail_down()
    api = make_api()
    with capture_logs() as logs:
        r = await api.register("lena@hc-test.ch", name="Lena")
    assert r.status_code == 201 and r.json() == {"status": "ok"}
    assert any(e["event"] == "email_send_failed" and e["purpose"] == "email_verify" for e in logs)
    assert "lena@hc-test.ch" not in repr(logs)
    me = (await api.get("/v1/me")).json()
    assert me["email"] == "lena@hc-test.ch" and me["email_verified"] is False

    # an explicit resend reports the outage instead of pretending success
    resend = await api.post("/v1/me/email/verify")
    assert resend.status_code == 503
    assert resend.json()["type"].endswith(":email-unavailable")

    monkeypatch.undo()  # provider back
    before = len(outbox.outbox)
    assert (await api.post("/v1/me/email/verify")).status_code == 202
    assert len(outbox.outbox) == before + 1 and "/auth/verify?token=" in outbox.outbox[-1].text


async def test_reset_magic_link_invitation_and_feedback(
    make_api: Callable[[], Api], mail_down: Callable[[], None]
) -> None:
    api = make_api()
    ids = await setup_club(api)
    mail_down()
    email = api.user["email"]
    for path in ("/v1/auth/password/forgot", "/v1/auth/magic-link"):
        assert (await make_api().post(path, json={"email": email})).status_code == 202

    inv = await api.post(
        f"/v1/orgs/{ids['org']}/invitations",
        json={"email": "tom@hc-test.ch", "team_id": ids["team"], "team_role": "player"},
    )
    assert inv.status_code == 201
    listed = (await api.get(f"/v1/orgs/{ids['org']}/invitations")).json()
    assert any(i["email"] == "tom@hc-test.ch" for i in listed)

    # feedback is nothing but the mail: a clear, translated problem instead of a bare 500
    fb = await api.post(f"/v1/orgs/{ids['org']}/feedback", json={"message": "Upload hängt"})
    assert fb.status_code == 503 and fb.json()["type"].endswith(":email-unavailable")


async def test_onboarding_series_retries_failed_mail(
    make_api: Callable[[], Api],
    outbox: MemoryEmailSender,
    mail_down: Callable[[], None],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = make_api()
    await setup_club(api)

    async def run() -> int:
        async with open_session() as db:
            ctx = Ctx(
                db=db,
                settings=api.app.state.settings,
                email=api.app.state.email,
                storage=api.app.state.storage,
            )
            await enable_system_access(db, reason="test")
            await db.execute(text("UPDATE users SET email_verified_at = now()"))
            n = await support.run_series(ctx, datetime.now(UTC) + timedelta(hours=1))
            await db.commit()
            return n

    mail_down()
    assert await run() == 0  # not marked as sent
    monkeypatch.undo()
    assert await run() == 1 and outbox.outbox[-1].subject == "Willkommen bei Handball AI"

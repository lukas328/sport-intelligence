"""Support, help and onboarding (addendum 01, 4.11)."""

from __future__ import annotations

import base64
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from handball_api.core.db import enable_system_access, open_session
from handball_api.core.email import MemoryEmailSender
from handball_api.core.jobs import MemoryJobQueue
from handball_api.services import support
from handball_api.services.context import Ctx

from .conftest import Api, setup_club
from .test_identity_sync import _ingest
from .test_matches import new_match, upload

pytestmark = pytest.mark.usefixtures("clean_db")


def test_failure_codes() -> None:
    assert support.failure_code("calibration: no court lines found") == "calibration"
    assert support.failure_code("ProbeError: no video stream") == "unreadable"
    assert support.failure_code("TimeoutError: timed out") == "timeout"
    assert support.failure_code(None) == "generic"


async def test_failed_analysis_is_credited(
    make_api: Callable[[], Api], outbox: MemoryEmailSender
) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    m = await new_match(api, ids)
    vid = (await upload(api, ids, m["id"], b"v" * 100))["id"]
    jobs: MemoryJobQueue = api.app.state.jobs
    await _ingest(api, jobs.jobs[-1][2], jobs.jobs[-1][3]["prefix"])
    token = {"x-internal-token": api.app.state.settings.internal_token.get_secret_value()}
    r = await api.http.post(
        f"/internal/jobs/{jobs.jobs[-1][2]}",
        headers=token,
        json={"status": "failed", "progress": 0.3, "error": "calibration: no court lines found"},
    )
    assert r.status_code == 200
    a = (await api.get(f"/v1/orgs/{org}/videos/{vid}/analysis")).json()
    assert (a["status"], a["error_code"]) == ("failed", "calibration")
    notes = (await api.get(f"/v1/orgs/{org}/me/notifications")).json()["items"]
    assert notes[0]["kind"] == "analysis_failed" and notes[0]["params"]["reason"] == "calibration"
    # the coach also gets an e-mail naming the match and the way out (UX test H06, B29)
    assert notes[0]["params"]["opponent"]
    mail = outbox.outbox[-1]
    assert notes[0]["params"]["opponent"] in mail.subject
    assert "liess sich nicht auswerten" in mail.subject and f"/matches/{m['id']}" in mail.text
    usage = (await api.get(f"/v1/orgs/{org}/billing")).json()["usage"]
    assert usage["max_matches_per_season"] == 0  # the failed match does not count


async def test_feedback_checklist_demo(
    make_api: Callable[[], Api], outbox: MemoryEmailSender
) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    png = "data:image/png;base64," + base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * 20).decode()
    r = await api.post(
        f"/v1/orgs/{org}/feedback",
        json={
            "message": "Der Upload hängt bei 99 %",
            "page": "/app/x/matches/y",
            "browser": "Firefox 140",
            "screenshot": png,
        },
    )
    assert r.status_code == 204
    mail = outbox.outbox[-1]
    assert (
        mail.to == "support@handball-intelligence.com"
        and "page: /app/x/matches/y" in mail.text
        and "HC Test" in mail.text
    )
    assert mail.attachments[0][0] == "screenshot.png"
    bad = await api.post(
        f"/v1/orgs/{org}/feedback",
        json={"message": "x" * 5, "screenshot": "data:text/html;base64,PGI+"},
    )
    assert bad.status_code == 422

    steps = {
        s["key"]: s["done"] for s in (await api.get(f"/v1/orgs/{org}/onboarding/checklist")).json()
    }
    assert steps["team"] is True and steps["demo"] is False and steps["upload"] is False
    demo = await api.post(f"/v1/orgs/{org}/teams/{ids['team']}/demo-match")
    assert demo.status_code == 201 and demo.json()["is_demo"] is True
    again = await api.post(f"/v1/orgs/{org}/teams/{ids['team']}/demo-match")
    assert again.json()["id"] == demo.json()["id"]
    stats = (await api.get(f"/v1/orgs/{org}/matches/{demo.json()['id']}/stats")).json()
    assert stats["own"]["shots"] >= 28 and stats["opponent"]["goals"] > 0
    steps = {
        s["key"]: s["done"] for s in (await api.get(f"/v1/orgs/{org}/onboarding/checklist")).json()
    }
    assert steps["demo"] is True
    assert (await api.get(f"/v1/orgs/{org}/billing")).json()["usage"]["max_matches_per_season"] == 0
    cfg = (await api.get("/v1/support/config")).json()
    assert cfg["chat"] is None and cfg["support_email"] == "support@handball-intelligence.com"


async def test_onboarding_series_and_unsubscribe(
    make_api: Callable[[], Api], outbox: MemoryEmailSender
) -> None:
    api = make_api()
    await setup_club(api)
    user_id = api.user["id"]

    async def run(days: int) -> int:
        async with open_session() as db:
            ctx = Ctx(
                db=db,
                settings=api.app.state.settings,
                email=api.app.state.email,
                storage=api.app.state.storage,
            )
            await enable_system_access(db, reason="test")
            await db.execute(text("UPDATE users SET email_verified_at = now()"))
            n = await support.run_series(ctx, datetime.now(UTC) + timedelta(days=days, hours=1))
            await db.commit()
            return n

    before = len(outbox.outbox)
    assert await run(0) == 1 and outbox.outbox[-1].subject == "Willkommen bei Handball Intelligence"
    assert await run(0) == 0
    assert (
        await run(5) == 1 and "Videositzung" in outbox.outbox[-1].subject
    )  # day 3, no backlog of day 1
    link = outbox.outbox[-1].text.rsplit(": ", 1)[1].strip()
    assert "/v1/onboarding/unsubscribe?u=" in link
    path = link.split("web.test", 1)[1] if "web.test" in link else link[link.index("/v1/") :]
    r = await api.http.get(path)
    assert r.status_code == 200 and "Abgemeldet" in r.text
    assert await run(8) == 0
    assert len(outbox.outbox) - before == 2
    assert (
        await api.http.get(f"/v1/onboarding/unsubscribe?u={user_id}&t=wrong")
    ).status_code == 404


def test_analysis_ready_mail_names_the_match() -> None:
    from handball_api.services.mail_templates import render

    mail = render(
        "analysis_ready", "de-CH", to="a@b.ch", name="Hans", team="HC Z", opponent="TV T", link="x"
    )
    assert mail.subject == "Die drei Dinge gegen TV T sind da"
    assert "HC Z gegen TV T" in mail.text and mail.text.endswith("x")


def test_after_the_analysis_the_mail_promises_only_what_is_there() -> None:
    """UX test N05 and N20: without three things the mail says the analysis is done and how many
    questions wait; an account without a name is greeted with «Hallo» alone."""
    from handball_api.services.mail_templates import render

    mail = render(
        "analysis_questions",
        "de-CH",
        to="hans.p130@example.ch",
        name="hans.p130",
        team="HC Z",
        opponent="TV T",
        link="x",
        questions=2,
    )
    assert mail.subject == "Die Analyse gegen TV T ist fertig"
    assert "drei Dinge" not in mail.text and "2 Fragen an dich" in mail.text
    assert mail.text.startswith("Hallo\n")
    # singular and plural as whole sentences, in every language (UX test round 3, final check)
    for loc, n, sentence in (
        ("de-CH", 1, "Eine Frage an dich hilft ihr weiter:"),
        ("de-CH", 2, "2 Fragen an dich helfen ihr weiter:"),
        ("en", 1, "One question for you helps it on:"),
        ("en", 2, "2 questions for you help it on:"),
        ("fr", 1, "Une question pour toi l'aide à avancer :"),
        ("fr", 2, "2 questions pour toi l'aident à avancer :"),
    ):
        mail_n = render(
            "analysis_questions",
            loc,
            to="a@b.ch",
            name="H",
            team="Z",
            opponent="T",
            link="x",
            questions=n,
        )
        assert sentence in mail_n.text, mail_n.text
    # further moments after the most important questions: the mail says so (real-video test G1)
    more = render(
        "analysis_questions",
        "de-CH",
        to="a@b.ch",
        name="H",
        team="Z",
        opponent="T",
        link="x",
        questions=12,
        more_moments=10,
    )
    assert "12 Fragen an dich helfen ihr weiter, danach können weitere Momente folgen:" in more.text
    named = render(
        "analysis_no_goals", "de-CH", to="a@b.ch", name="Hans", team="Z", opponent="T", link="x"
    )
    assert named.text.startswith("Hallo Hans\n") and "keine Tore" in named.text

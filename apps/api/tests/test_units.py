from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

import pyotp
import pytest

from handball_api.core.ratelimit import MemoryRateLimiter, parse_rate
from handball_api.core.security import (
    SecretBox,
    csrf_for_session,
    hash_password,
    verify_password,
    verify_totp,
)
from handball_api.models.enums import OrgRole, TeamRole
from handball_api.services.csv_import import decode, parse_roster_csv
from handball_api.services.mail_templates import render
from handball_api.services.orgs import current_season_bounds, detect_image_type
from handball_api.services.policies import (
    Action,
    Actor,
    TwoFactorPolicy,
    authorize,
    can,
    two_factor_missing,
    visible_team_ids,
)

TEAM = uuid.uuid4()
OTHER = uuid.uuid4()


def actor(role: OrgRole = OrgRole.MEMBER, team_role: TeamRole | None = None, **kw: object) -> Actor:
    return Actor(uuid.uuid4(), uuid.uuid4(), role, {TEAM: team_role} if team_role else {}, **kw)  # type: ignore[arg-type]


def test_can_team_actions() -> None:
    assert can(actor(OrgRole.ORG_ADMIN), Action.ROSTER_WRITE, OTHER)
    assert can(actor(team_role=TeamRole.COACH), Action.ROSTER_WRITE, TEAM)
    assert not can(actor(team_role=TeamRole.COACH), Action.ROSTER_WRITE, OTHER)
    assert not can(actor(team_role=TeamRole.ANALYST), Action.ROSTER_WRITE, TEAM)
    assert can(actor(team_role=TeamRole.ANALYST), Action.SEASON_WRITE, TEAM)
    assert can(actor(team_role=TeamRole.PLAYER), Action.ROSTER_READ, TEAM)
    assert not can(actor(team_role=TeamRole.GUEST), Action.TEAM_READ, TEAM)
    with pytest.raises(ValueError, match="needs a team"):
        can(actor(), Action.TEAM_READ)


def test_visible_teams() -> None:
    assert visible_team_ids(actor(OrgRole.ORG_ADMIN)) is None
    assert visible_team_ids(actor(team_role=TeamRole.PLAYER)) == {TEAM}
    assert visible_team_ids(actor(team_role=TeamRole.GUEST)) == set()


def test_two_factor_policy() -> None:
    policy = TwoFactorPolicy(required=True, grace_days=14)
    now = datetime.now(UTC)
    fresh = actor(OrgRole.ORG_ADMIN, org_created_at=now)
    old = actor(OrgRole.ORG_ADMIN, org_created_at=now - timedelta(days=30))
    assert not two_factor_missing(fresh, policy, now)
    assert two_factor_missing(old, policy, now)
    assert not two_factor_missing(
        actor(OrgRole.ORG_ADMIN, org_created_at=now - timedelta(days=30), has_2fa=True), policy
    )
    assert not two_factor_missing(old, TwoFactorPolicy(required=False, grace_days=0))
    assert two_factor_missing(actor(OrgRole.ORG_ADMIN), policy)
    with pytest.raises(Exception, match="two-factor"):
        authorize(old, Action.ORG_UPDATE, two_factor=policy)
    authorize(old, Action.ORG_READ, two_factor=policy)


def test_passwords_and_tokens() -> None:
    h = hash_password("correct-horse-1")
    assert h.startswith("$argon2id$")
    assert verify_password(h, "correct-horse-1")
    assert not verify_password(h, "wrong")
    assert not verify_password(None, "x")
    assert not verify_password("garbage", "x")
    assert csrf_for_session("k", "a") != csrf_for_session("k", "b")


def test_secret_box_and_totp() -> None:
    from cryptography.fernet import Fernet

    box = SecretBox(Fernet.generate_key().decode())
    assert box.decrypt(box.encrypt("s3cret")) == "s3cret"
    assert box.decrypt("not-a-token") is None
    secret = pyotp.random_base32()
    assert verify_totp(secret, pyotp.TOTP(secret).now())
    assert not verify_totp(secret, "abc")
    assert not verify_totp(secret, "12345")


async def test_memory_rate_limiter() -> None:
    rl = MemoryRateLimiter()
    assert parse_rate("3/60") == (3, 60)
    assert [await rl.hit("k", 2, 60) for _ in range(3)] == [True, True, False]
    assert await rl.hit("k", 2, 0)  # window elapsed
    rl.reset()


@pytest.mark.parametrize(
    ("today", "label", "start"),
    [
        (date(2026, 11, 2), "2026/27", date(2026, 7, 1)),
        (date(2027, 3, 1), "2026/27", date(2026, 7, 1)),
        (date(2027, 7, 1), "2027/28", date(2027, 7, 1)),
    ],
)
def test_season_bounds(today: date, label: str, start: date) -> None:
    lab, s, e = current_season_bounds(today)
    assert (lab, s) == (label, start)
    assert e == date(start.year + 1, 6, 30)


def test_detect_image_type() -> None:
    assert detect_image_type(b"\x89PNG\r\n\x1a\nxxxx") == "image/png"
    assert detect_image_type(b"\xff\xd8\xff\xe0") == "image/jpeg"
    assert detect_image_type(b"RIFF\x00\x00\x00\x00WEBPVP8 ") == "image/webp"
    assert detect_image_type(b"RIFF\x00\x00\x00\x00WAVE") is None
    assert detect_image_type(b"<svg") is None


def test_csv_variants() -> None:
    assert decode("Müller".encode("cp1252")) == "Müller"
    rows, errors = parse_roster_csv(
        b"first_name,last_name,position,secondary_positions,hand\nA,B,Kreis,RL/RR,gauche\n"
    )
    assert errors == []
    assert rows[0].main_position == "KM"
    assert rows[0].secondary_positions == ["RL", "RR"]
    assert rows[0].shooting_hand == "left"
    big = b"Vorname;Nachname\n" + b"A;B\n" * 201
    _rows, errs = parse_roster_csv(big)
    assert any("At most" in e.message for e in errs)
    _rows, errs = parse_roster_csv(b"x" * 200_001)
    assert "too large" in errs[0].message
    rows, errors = parse_roster_csv(b"Vorname;Nachname\n\nA;B\n;\n")
    assert len(rows) == 1


def test_mail_templates_have_no_long_dashes() -> None:
    for tpl in ("magic_link", "invitation"):
        for locale in ("de-CH", "en", "fr", "xx"):
            mail = render(
                tpl,
                locale,
                to="a@b.ch",
                name="N",
                link="L",
                minutes=15,
                inviter="I",
                org="O",
                team="",
                days=14,
            )
            assert "\u2014" not in mail.text
            assert "\u2013" not in mail.text
            assert "ß" not in mail.text


def test_production_refuses_dev_secrets() -> None:
    from pydantic import SecretStr

    from handball_api.core.config import Settings
    from handball_api.main import check_production_secrets

    check_production_secrets(Settings(env="local"))
    with pytest.raises(RuntimeError, match="HB_SECRET_KEY"):
        check_production_secrets(Settings(env="production", cookie_secure=True))
    with pytest.raises(RuntimeError, match="COOKIE_SECURE"):
        check_production_secrets(
            Settings(
                env="production",
                secret_key=SecretStr("x" * 40),
                encryption_key=SecretStr("y" * 44),
                internal_token=SecretStr("z" * 32),
            )
        )
    check_production_secrets(
        Settings(
            env="production",
            cookie_secure=True,
            secret_key=SecretStr("x" * 40),
            encryption_key=SecretStr("y" * 44),
            internal_token=SecretStr("z" * 32),
        )
    )


def test_policy_doc_is_up_to_date() -> None:
    from pathlib import Path

    from handball_api.services.policies import matrix_markdown

    doc = Path(__file__).resolve().parents[3] / "docs" / "policy-matrix.md"
    assert doc.read_text() == matrix_markdown(), "run `make policy-doc`"


def test_signing_roundtrip() -> None:
    from handball_api.core.signing import sign, unsign

    v = sign("k", {"a": 1}, 60, "p")
    assert unsign("k", v, "p") == {"a": 1}
    assert unsign("other", v, "p") is None
    assert unsign("k", v, "other-purpose") is None
    assert unsign("k", sign("k", {"a": 1}, -1, "p"), "p") is None
    assert unsign("k", "garbage", "p") is None


async def test_tracing_records_spans() -> None:
    from httpx import ASGITransport, AsyncClient
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    from handball_api.core.config import Settings
    from handball_api.core.storage import MemoryStorage
    from handball_api.core.telemetry import setup_tracing
    from handball_api.main import create_app

    settings = Settings(env="test", email_backend="memory", rate_limit_backend="memory")
    plain = create_app(settings, storage=MemoryStorage())
    assert setup_tracing(plain, settings) is False
    exporter = InMemorySpanExporter()
    app = create_app(settings, storage=MemoryStorage())
    assert setup_tracing(app, settings, exporter) is True
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        await c.get("/v1/openapi.json")
    app.state.tracer_provider.force_flush()
    assert any("openapi" in s.name for s in exporter.get_finished_spans())


def test_rq_queue_has_socket_timeouts() -> None:
    from handball_api.core.jobs import RqJobQueue

    q = RqJobQueue("redis://127.0.0.1:1/0")
    kwargs = q._conn.connection_pool.connection_kwargs
    assert (kwargs["socket_timeout"], kwargs["socket_connect_timeout"]) == (5, 5)


async def test_ctx_enqueue_runs_off_the_event_loop() -> None:
    import threading
    from typing import Any, cast

    from handball_api.services.context import Ctx

    seen: list[tuple[str, str, str, dict[str, Any], int | None, bool]] = []
    loop_thread = threading.get_ident()

    class Queue:
        def enqueue(
            self,
            queue: str,
            func: str,
            job_id: str,
            kwargs: dict[str, Any],
            timeout_s: int | None = None,
        ) -> None:
            off_loop = threading.get_ident() != loop_thread
            seen.append((queue, func, job_id, kwargs, timeout_s, off_loop))

        def depths(self) -> dict[str, int]:
            return {}

    none = cast(Any, None)
    ctx = Ctx(db=none, settings=none, email=none, storage=none, jobs=Queue())
    await ctx.enqueue("gpu", "a.b", "j1", {"x": 1}, 60)
    assert seen == [("gpu", "a.b", "j1", {"x": 1}, 60, True)]
    with pytest.raises(RuntimeError):
        await Ctx(db=none, settings=none, email=none, storage=none).enqueue("gpu", "a.b", "j2", {})

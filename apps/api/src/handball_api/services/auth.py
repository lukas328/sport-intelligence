"""Registration, login (password, magic link, TOTP), sessions (ADR 008)."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

import httpx
from sqlalchemy import delete, select

from handball_api.core.email import try_send
from handball_api.core.errors import ProblemError
from handball_api.core.logging import get_logger
from handball_api.core.security import (
    SecretBox,
    csrf_for_session,
    hash_password,
    hash_token,
    needs_rehash,
    new_token,
    new_totp_secret,
    totp_uri,
    verify_password,
    verify_totp,
)
from handball_api.models import AuthSession, AuthToken, User
from handball_api.models.enums import TokenPurpose
from handball_api.schemas.auth import LoginIn, MeUpdate, RegisterIn
from handball_api.services import audit
from handball_api.services.context import Ctx
from handball_api.services.mail_templates import render

LAST_SEEN_RESOLUTION = timedelta(minutes=5)


@dataclass(frozen=True, slots=True)
class IssuedSession:
    token: str
    csrf: str
    mfa_pending: bool
    expires_at: datetime


log = get_logger("handball_api.auth")


def _now() -> datetime:
    return datetime.now(UTC)


def _box(ctx: Ctx) -> SecretBox:
    return SecretBox(ctx.settings.encryption_key.get_secret_value())


COMMON_PASSWORDS = frozenset(
    {
        "1234567890",
        "12345678910",
        "123456789a",
        "password123",
        "password1!",
        "passwort123",
        "passwort1!",
        "qwertzuiop",
        "qwertyuiop",
        "1q2w3e4r5t",
        "asdfghjkl1",
        "iloveyou12",
        "handball12",
        "handball123",
        "handball2026",
        "hallo12345",
        "sommer2026",
        "winter2026",
        "fussball123",
        "schweiz123",
        "zuerich123",
        "abcdefghij",
        "0000000000",
        "1111111111",
        "letmein123",
        "welcome123",
        "willkommen1",
        "admin12345",
        "trustno1234",
        "dragon12345",
    }
)


def validate_password(ctx: Ctx, password: str, email: str) -> None:
    """Length, no e-mail inside, not a common password (ASVS V2.1). Breach check: see is_pwned."""
    problems = []
    if len(password) < ctx.settings.password_min_length:
        problems.append(f"at least {ctx.settings.password_min_length} characters")
    if password.lower() == email.lower() or password.lower() in email.lower():
        problems.append("must not contain the e-mail address")
    if password.lower() in COMMON_PASSWORDS or len(set(password)) <= 2:
        problems.append("too common")
    if problems:
        raise ProblemError(422, "weak-password", "Password: " + ", ".join(problems))


async def check_not_pwned(ctx: Ctx, password: str) -> None:
    """Optional Have I Been Pwned range check (k-anonymity: only 5 hash characters leave us).

    Fails open on network errors so sign-up never depends on a third party.
    """
    if not ctx.settings.pwned_check:
        return
    digest = hashlib.sha1(password.encode(), usedforsecurity=False).hexdigest().upper()
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(
                f"https://api.pwnedpasswords.com/range/{digest[:5]}",
                headers={"add-padding": "true", "user-agent": "handball-ai"},
            )
        r.raise_for_status()
    except httpx.HTTPError:
        log.warning("pwned_check_unavailable")
        return
    suffix = digest[5:]
    for line in r.text.splitlines():
        found, _, count = line.partition(":")
        if found == suffix and count.strip() != "0":
            raise ProblemError(422, "weak-password", "Password: found in known data breaches")


async def issue_session(
    ctx: Ctx,
    user: User,
    *,
    mfa_pending: bool,
    user_agent: str | None,
    method: str = "password",
) -> IssuedSession:
    token = new_token()
    expires = _now() + timedelta(hours=ctx.settings.session_ttl_hours)
    if mfa_pending:
        expires = _now() + timedelta(minutes=10)
    ctx.db.add(
        AuthSession(
            user_id=user.id,
            token_hash=hash_token(token),
            mfa_pending=mfa_pending,
            mfa_verified=False,
            expires_at=expires,
            user_agent=(user_agent or "")[:300] or None,
            ip=ctx.ip,
            method=method,
        )
    )
    if not mfa_pending:
        user.last_login_at = _now()
    return IssuedSession(
        token=token,
        csrf=csrf_for_session(ctx.settings.secret_key.get_secret_value(), token),
        mfa_pending=mfa_pending,
        expires_at=expires,
    )


async def register(
    ctx: Ctx, data: RegisterIn, user_agent: str | None
) -> tuple[User, IssuedSession]:
    if not data.accept_terms:
        raise ProblemError(422, "terms-not-accepted", "Terms must be accepted")
    validate_password(ctx, data.password, data.email)
    await check_not_pwned(ctx, data.password)
    exists = await ctx.db.scalar(select(User.id).where(User.email == data.email))
    if exists:
        raise ProblemError(409, "email-taken", "An account with this e-mail already exists")
    user = User(
        email=data.email,
        name=data.name,
        locale=data.locale,
        password_hash=await asyncio.to_thread(hash_password, data.password),
        terms_accepted_at=_now(),
    )
    ctx.db.add(user)
    await ctx.db.flush()
    ctx.user_id = user.id
    await audit.record(ctx, "user.registered", target_type="user", target_id=user.id)
    if not data.invitation_token:  # invitations prove the address already
        # A mail outage must not lose the account: the banner in the app offers a resend.
        await send_email_verification(ctx, user)
    return user, await issue_session(ctx, user, mfa_pending=False, user_agent=user_agent)


async def login(ctx: Ctx, data: LoginIn, user_agent: str | None) -> IssuedSession:
    user = await ctx.db.scalar(select(User).where(User.email == data.email))
    # argon2 takes tens of milliseconds of CPU: off the event loop
    if user is None or not await asyncio.to_thread(
        verify_password, user.password_hash if user else None, data.password
    ):
        raise ProblemError(401, "invalid-credentials", "E-mail or password is wrong")
    if user.password_hash and needs_rehash(user.password_hash):
        user.password_hash = await asyncio.to_thread(hash_password, data.password)
    ctx.user_id = user.id
    await audit.record(ctx, "user.login", target_type="user", target_id=user.id)
    return await issue_session(ctx, user, mfa_pending=user.totp_enabled, user_agent=user_agent)


RECOVERY_CODES = 10


def _recovery_hash(ctx: Ctx, code: str) -> str:
    normalised = code.strip().lower().replace("-", "").replace(" ", "")
    key = ctx.settings.secret_key.get_secret_value().encode()
    return hmac.new(key, b"recovery:" + normalised.encode(), hashlib.sha256).hexdigest()


def new_recovery_codes(ctx: Ctx, user: User) -> list[str]:
    """Ten one-time codes like `k7m2-x9qp`; only their HMAC is stored."""
    alphabet = "abcdefghjkmnpqrstuvwxyz23456789"
    codes = [
        "-".join("".join(secrets.choice(alphabet) for _ in range(4)) for _ in range(2))
        for _ in range(RECOVERY_CODES)
    ]
    user.recovery_codes = [_recovery_hash(ctx, c) for c in codes]
    return codes


def _use_recovery_code(ctx: Ctx, user: User, code: str) -> bool:
    digest = _recovery_hash(ctx, code)
    remaining = list(user.recovery_codes or [])
    for stored in remaining:
        if hmac.compare_digest(stored, digest):
            remaining.remove(stored)
            user.recovery_codes = remaining
            return True
    return False


async def complete_totp(ctx: Ctx, session: AuthSession, user: User, code: str) -> None:
    if not session.mfa_pending:
        raise ProblemError(409, "no-totp-pending", "No second factor pending")
    secret = _box(ctx).decrypt(user.totp_secret_enc or "")
    ok = secret is not None and secret != "" and verify_totp(secret, code)
    if not ok and len(code.strip()) > 8 and _use_recovery_code(ctx, user, code):
        ok = True
        await audit.record(
            ctx,
            "user.recovery_code_used",
            target_type="user",
            target_id=user.id,
            data={"remaining": len(user.recovery_codes)},
        )
    if not ok:
        raise ProblemError(401, "invalid-totp", "The code is wrong or expired")
    session.mfa_pending = False
    session.mfa_verified = True
    session.expires_at = _now() + timedelta(hours=ctx.settings.session_ttl_hours)
    user.last_login_at = _now()


async def resolve_session(ctx: Ctx, token: str) -> tuple[AuthSession, User] | None:
    row = (
        await ctx.db.execute(
            select(AuthSession, User)
            .join(User, User.id == AuthSession.user_id)
            .where(AuthSession.token_hash == hash_token(token))
        )
    ).first()
    if row is None:
        return None
    session, user = row
    now = _now()
    if session.expires_at <= now:
        return None
    if session.last_seen_at is None or now - session.last_seen_at > LAST_SEEN_RESOLUTION:
        session.last_seen_at = now
    return session, user


async def logout(ctx: Ctx, session: AuthSession) -> None:
    await ctx.db.execute(delete(AuthSession).where(AuthSession.id == session.id))


async def start(ctx: Ctx, email: str, locale: str, next_path: str | None) -> None:
    """The passwordless start of the public entry: a new address gets an account without a
    password (saving accepts the terms), every address gets a sign-in link that leads to
    `next_path`. Same answer either way (no account enumeration)."""
    user = await ctx.db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(
            email=email,
            # the name is asked later (Ich); until then the part before the @
            name=email.split("@", 1)[0][:120] or email[:120],
            locale=locale,
            password_hash=None,
            terms_accepted_at=_now(),
        )
        ctx.db.add(user)
        await ctx.db.flush()
        await audit.record(
            ctx, "user.registered_passwordless", target_type="user", target_id=user.id
        )
    await request_magic_link(ctx, email, next_path)


async def request_magic_link(ctx: Ctx, email: str, next_path: str | None = None) -> None:
    """Always succeeds (no account enumeration). Sends a link only if the account exists."""
    user = await ctx.db.scalar(select(User).where(User.email == email))
    if user is None:
        return
    token = new_token()
    ctx.db.add(
        AuthToken(
            purpose=TokenPurpose.MAGIC_LINK,
            token_hash=hash_token(token),
            user_id=user.id,
            email=user.email,
            expires_at=_now() + timedelta(minutes=ctx.settings.magic_link_ttl_minutes),
        )
    )
    link = f"{ctx.settings.web_base_url}/auth/magic?token={token}"
    if next_path and next_path.startswith("/") and not next_path.startswith("//"):
        link += f"&next={quote(next_path, safe='')}"
    # same answer either way (no account enumeration); a failure is logged
    await try_send(
        ctx.email,
        render(
            "magic_link",
            user.locale,
            to=user.email,
            name=user.name,
            link=link,
            minutes=ctx.settings.magic_link_ttl_minutes,
        ),
        "magic_link",
        user_id=str(user.id),
    )


async def consume_magic_link(ctx: Ctx, token: str, user_agent: str | None) -> IssuedSession:
    row = await ctx.db.scalar(
        select(AuthToken)
        .where(AuthToken.token_hash == hash_token(token))
        .where(AuthToken.purpose == TokenPurpose.MAGIC_LINK)
        .with_for_update()
    )
    if row is None or row.used_at is not None or row.expires_at <= _now() or row.user_id is None:
        raise ProblemError(400, "invalid-token", "The link is invalid or expired")
    row.used_at = _now()
    user = await ctx.db.get(User, row.user_id)
    if user is None:
        raise ProblemError(400, "invalid-token", "The link is invalid or expired")
    user.email_verified_at = user.email_verified_at or _now()
    ctx.user_id = user.id
    await audit.record(ctx, "user.login_magic_link", target_type="user", target_id=user.id)
    return await issue_session(
        ctx, user, mfa_pending=user.totp_enabled, user_agent=user_agent, method="magic_link"
    )


async def update_me(ctx: Ctx, user: User, data: MeUpdate) -> User:
    if data.name is not None:
        user.name = data.name
    if data.locale is not None:
        user.locale = data.locale
    return user


async def totp_setup(ctx: Ctx, user: User) -> tuple[str, str]:
    if user.totp_enabled:
        raise ProblemError(409, "totp-already-enabled", "Two-factor authentication is already on")
    secret = new_totp_secret()
    user.totp_secret_enc = _box(ctx).encrypt(secret)
    return secret, totp_uri(secret, user.email)


async def totp_enable(ctx: Ctx, user: User, session: AuthSession, code: str) -> list[str]:
    secret = _box(ctx).decrypt(user.totp_secret_enc or "")
    if not secret:
        raise ProblemError(409, "totp-not-set-up", "Start the setup first")
    if not verify_totp(secret, code):
        raise ProblemError(422, "invalid-totp", "The code is wrong or expired")
    user.totp_enabled_at = _now()
    session.mfa_verified = True
    await audit.record(ctx, "user.totp_enabled", target_type="user", target_id=user.id)
    return new_recovery_codes(ctx, user)


async def regenerate_recovery_codes(ctx: Ctx, user: User, code: str) -> list[str]:
    secret = _box(ctx).decrypt(user.totp_secret_enc or "")
    if not user.totp_enabled or not secret:
        raise ProblemError(409, "totp-not-enabled", "Two-factor authentication is off")
    if not verify_totp(secret, code):
        raise ProblemError(422, "invalid-totp", "The code is wrong or expired")
    await audit.record(
        ctx, "user.recovery_codes_regenerated", target_type="user", target_id=user.id
    )
    return new_recovery_codes(ctx, user)


async def totp_disable(ctx: Ctx, user: User, code: str) -> None:
    secret = _box(ctx).decrypt(user.totp_secret_enc or "")
    if not user.totp_enabled or not secret:
        raise ProblemError(409, "totp-not-enabled", "Two-factor authentication is off")
    if not verify_totp(secret, code):
        raise ProblemError(422, "invalid-totp", "The code is wrong or expired")
    user.totp_enabled_at = None
    user.totp_secret_enc = None
    user.recovery_codes = []
    await audit.record(ctx, "user.totp_disabled", target_type="user", target_id=user.id)


# ---- single-use tokens (password reset, e-mail verification) ------------------------------


async def _issue_token(ctx: Ctx, user: User, purpose: TokenPurpose, ttl: timedelta) -> str:
    token = new_token()
    ctx.db.add(
        AuthToken(
            purpose=purpose,
            token_hash=hash_token(token),
            user_id=user.id,
            email=user.email,
            expires_at=_now() + ttl,
        )
    )
    return token


async def _consume_token(ctx: Ctx, token: str, purpose: TokenPurpose) -> User:
    row = await ctx.db.scalar(
        select(AuthToken)
        .where(AuthToken.token_hash == hash_token(token), AuthToken.purpose == purpose)
        .with_for_update()
    )
    if row is None or row.used_at is not None or row.expires_at <= _now() or row.user_id is None:
        raise ProblemError(400, "invalid-token", "The link is invalid or expired")
    row.used_at = _now()
    user = await ctx.db.get(User, row.user_id)
    if user is None or user.email.lower() != row.email.lower():
        raise ProblemError(400, "invalid-token", "The link is invalid or expired")
    return user


async def request_password_reset(ctx: Ctx, email: str) -> None:
    """Always succeeds (no account enumeration)."""
    user = await ctx.db.scalar(select(User).where(User.email == email))
    if user is None:
        return
    minutes = ctx.settings.password_reset_ttl_minutes
    token = await _issue_token(ctx, user, TokenPurpose.PASSWORD_RESET, timedelta(minutes=minutes))
    # same answer either way (no account enumeration); a failure is logged
    await try_send(
        ctx.email,
        render(
            "password_reset",
            user.locale,
            to=user.email,
            name=user.name,
            minutes=minutes,
            link=f"{ctx.settings.web_base_url}/auth/reset?token={token}",
        ),
        "password_reset",
        user_id=str(user.id),
    )
    await audit.record(
        ctx,
        "user.password_reset_requested",
        target_type="user",
        target_id=user.id,
        actor_id=user.id,
    )


async def reset_password(
    ctx: Ctx, token: str, password: str, user_agent: str | None
) -> IssuedSession:
    user = await _consume_token(ctx, token, TokenPurpose.PASSWORD_RESET)
    validate_password(ctx, password, user.email)
    await check_not_pwned(ctx, password)
    user.password_hash = await asyncio.to_thread(hash_password, password)
    user.email_verified_at = user.email_verified_at or _now()  # the mail reached the user
    await ctx.db.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
    ctx.user_id = user.id
    await audit.record(ctx, "user.password_reset", target_type="user", target_id=user.id)
    return await issue_session(
        ctx, user, mfa_pending=user.totp_enabled, user_agent=user_agent, method="password_reset"
    )


async def send_email_verification(ctx: Ctx, user: User) -> bool:
    """Returns False when the mail provider failed (logged); the token stays valid for a resend."""
    if user.email_verified_at is not None:
        return True
    hours = ctx.settings.email_verify_ttl_hours
    token = await _issue_token(ctx, user, TokenPurpose.EMAIL_VERIFY, timedelta(hours=hours))
    return await try_send(
        ctx.email,
        render(
            "email_verify",
            user.locale,
            to=user.email,
            name=user.name,
            hours=hours,
            link=f"{ctx.settings.web_base_url}/auth/verify?token={token}",
        ),
        "email_verify",
        user_id=str(user.id),
    )


async def resend_email_verification(ctx: Ctx, user: User) -> None:
    """The user asked for the mail explicitly, so a provider failure is reported (503)."""
    if not await send_email_verification(ctx, user):
        raise ProblemError(
            503, "email-unavailable", "The e-mail could not be sent; please try again later"
        )


async def verify_email(ctx: Ctx, token: str) -> User:
    user = await _consume_token(ctx, token, TokenPurpose.EMAIL_VERIFY)
    user.email_verified_at = user.email_verified_at or _now()
    await audit.record(
        ctx, "user.email_verified", target_type="user", target_id=user.id, actor_id=user.id
    )
    return user


async def change_password(
    ctx: Ctx, user: User, session: AuthSession, current: str | None, new: str
) -> None:
    # Accounts created via Google/Apple or magic link may have no password yet.
    if user.password_hash and not await asyncio.to_thread(
        verify_password, user.password_hash, current or ""
    ):
        raise ProblemError(403, "invalid-credentials", "The current password is wrong")
    validate_password(ctx, new, user.email)
    await check_not_pwned(ctx, new)
    user.password_hash = await asyncio.to_thread(hash_password, new)
    await ctx.db.execute(
        delete(AuthSession).where(AuthSession.user_id == user.id, AuthSession.id != session.id)
    )
    await audit.record(ctx, "user.password_changed", target_type="user", target_id=user.id)


async def list_sessions(ctx: Ctx, user: User) -> list[AuthSession]:
    rows = await ctx.db.scalars(
        select(AuthSession)
        .where(
            AuthSession.user_id == user.id,
            AuthSession.expires_at > _now(),
            AuthSession.mfa_pending.is_(False),
        )
        .order_by(AuthSession.created_at.desc())
    )
    return list(rows.all())


async def revoke_session(ctx: Ctx, user: User, session_id: uuid.UUID) -> None:
    res = await ctx.db.execute(
        delete(AuthSession).where(AuthSession.id == session_id, AuthSession.user_id == user.id)
    )
    if res.rowcount == 0:  # type: ignore[attr-defined]
        raise ProblemError(404, "not-found", "Session not found")
    await audit.record(ctx, "user.session_revoked", target_type="session", target_id=session_id)


async def revoke_other_sessions(ctx: Ctx, user: User, current: AuthSession) -> None:
    await ctx.db.execute(
        delete(AuthSession).where(AuthSession.user_id == user.id, AuthSession.id != current.id)
    )
    await audit.record(ctx, "user.sessions_revoked", target_type="user", target_id=user.id)

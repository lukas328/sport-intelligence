"""Registration, login (password, magic link, TOTP), sessions (ADR 008)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select

from handball_api.core.errors import ProblemError
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


def _now() -> datetime:
    return datetime.now(UTC)


def _box(ctx: Ctx) -> SecretBox:
    return SecretBox(ctx.settings.encryption_key.get_secret_value())


def validate_password(ctx: Ctx, password: str, email: str) -> None:
    problems = []
    if len(password) < ctx.settings.password_min_length:
        problems.append(f"at least {ctx.settings.password_min_length} characters")
    if password.lower() == email.lower() or password.lower() in email.lower():
        problems.append("must not contain the e-mail address")
    if problems:
        raise ProblemError(422, "weak-password", "Password: " + ", ".join(problems))


async def issue_session(
    ctx: Ctx, user: User, *, mfa_pending: bool, user_agent: str | None
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
    exists = await ctx.db.scalar(select(User.id).where(User.email == data.email))
    if exists:
        raise ProblemError(409, "email-taken", "An account with this e-mail already exists")
    user = User(
        email=data.email,
        name=data.name,
        locale=data.locale,
        password_hash=hash_password(data.password),
        terms_accepted_at=_now(),
    )
    ctx.db.add(user)
    await ctx.db.flush()
    ctx.user_id = user.id
    await audit.record(ctx, "user.registered", target_type="user", target_id=user.id)
    return user, await issue_session(ctx, user, mfa_pending=False, user_agent=user_agent)


async def login(ctx: Ctx, data: LoginIn, user_agent: str | None) -> IssuedSession:
    user = await ctx.db.scalar(select(User).where(User.email == data.email))
    if user is None or not verify_password(user.password_hash if user else None, data.password):
        raise ProblemError(401, "invalid-credentials", "E-mail or password is wrong")
    if user.password_hash and needs_rehash(user.password_hash):
        user.password_hash = hash_password(data.password)
    ctx.user_id = user.id
    await audit.record(ctx, "user.login", target_type="user", target_id=user.id)
    return await issue_session(ctx, user, mfa_pending=user.totp_enabled, user_agent=user_agent)


async def complete_totp(ctx: Ctx, session: AuthSession, user: User, code: str) -> None:
    if not session.mfa_pending:
        raise ProblemError(409, "no-totp-pending", "No second factor pending")
    secret = _box(ctx).decrypt(user.totp_secret_enc or "")
    if not secret or not verify_totp(secret, code):
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


async def request_magic_link(ctx: Ctx, email: str) -> None:
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
    await ctx.email.send(
        render(
            "magic_link",
            user.locale,
            to=user.email,
            name=user.name,
            link=link,
            minutes=ctx.settings.magic_link_ttl_minutes,
        )
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
    return await issue_session(ctx, user, mfa_pending=user.totp_enabled, user_agent=user_agent)


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


async def totp_enable(ctx: Ctx, user: User, session: AuthSession, code: str) -> None:
    secret = _box(ctx).decrypt(user.totp_secret_enc or "")
    if not secret:
        raise ProblemError(409, "totp-not-set-up", "Start the setup first")
    if not verify_totp(secret, code):
        raise ProblemError(422, "invalid-totp", "The code is wrong or expired")
    user.totp_enabled_at = _now()
    session.mfa_verified = True
    await audit.record(ctx, "user.totp_enabled", target_type="user", target_id=user.id)


async def totp_disable(ctx: Ctx, user: User, code: str) -> None:
    secret = _box(ctx).decrypt(user.totp_secret_enc or "")
    if not user.totp_enabled or not secret:
        raise ProblemError(409, "totp-not-enabled", "Two-factor authentication is off")
    if not verify_totp(secret, code):
        raise ProblemError(422, "invalid-totp", "The code is wrong or expired")
    user.totp_enabled_at = None
    user.totp_secret_enc = None
    await audit.record(ctx, "user.totp_disabled", target_type="user", target_id=user.id)

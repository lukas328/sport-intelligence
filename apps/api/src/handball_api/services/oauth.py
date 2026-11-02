"""Sign-in with Google and Apple (ADR 010): start, callback, account linking."""

from __future__ import annotations

import contextlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select

from handball_api.core.errors import ProblemError
from handball_api.core.oidc import (
    OidcClient,
    OidcError,
    OidcIdentity,
    ProviderConfig,
    authorize_url,
    client_secret,
    enabled_providers,
    pkce_pair,
)
from handball_api.core.signing import sign, unsign
from handball_api.models import OAuthIdentity, User
from handball_api.models.enums import OAuthProvider
from handball_api.services import audit
from handball_api.services import invitations as invitation_service
from handball_api.services.auth import IssuedSession, issue_session
from handball_api.services.context import Ctx

STATE_PURPOSE = "oauth-state"
STATE_TTL_S = 600


def redirect_uri(ctx: Ctx, provider: str) -> str:
    return f"{ctx.settings.web_base_url}/v1/auth/oauth/{provider}/callback"


def _provider(ctx: Ctx, provider: str) -> ProviderConfig:
    p = enabled_providers(ctx.settings).get(provider)
    if p is None:
        raise ProblemError(404, "not-found", "Sign-in provider not available")
    return p


def start(ctx: Ctx, provider: str, next_path: str, invite: str | None) -> tuple[str, str]:
    """Returns (authorization URL, signed state cookie)."""
    p = _provider(ctx, provider)
    state, nonce = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
    verifier, challenge = pkce_pair()
    cookie = sign(
        ctx.settings.secret_key.get_secret_value(),
        {"p": provider, "s": state, "n": nonce, "v": verifier, "next": next_path, "inv": invite},
        STATE_TTL_S,
        STATE_PURPOSE,
    )
    return authorize_url(p, redirect_uri(ctx, provider), state, nonce, challenge), cookie


@dataclass(frozen=True)
class CallbackResult:
    session: IssuedSession
    next_path: str
    created: bool


async def callback(
    ctx: Ctx,
    client: OidcClient,
    provider: str,
    code: str | None,
    state: str | None,
    cookie: str | None,
    user_agent: str | None,
    apple_user_name: str | None = None,
) -> CallbackResult:
    p = _provider(ctx, provider)
    data = unsign(ctx.settings.secret_key.get_secret_value(), cookie or "", STATE_PURPOSE)
    if not data or data.get("p") != provider or not state or data.get("s") != state or not code:
        raise ProblemError(400, "oauth-state", "Sign-in expired, please try again")
    try:
        id_token = await client.exchange(
            p, code, redirect_uri(ctx, provider), data["v"], client_secret(p, ctx.settings)
        )
        identity = await client.verify(p, id_token, data["n"])
    except OidcError as exc:
        raise ProblemError(400, "oauth-failed", "Sign-in with the provider failed") from exc
    user, created = await resolve_user(ctx, identity, apple_user_name)
    ctx.user_id = user.id
    if data.get("inv"):
        # On failure the invitation page shows the reason when the user opens it again.
        with contextlib.suppress(ProblemError):
            await invitation_service.accept(ctx, str(data["inv"]), user)
    await audit.record(
        ctx,
        f"user.login_{provider}",
        target_type="user",
        target_id=user.id,
        data={"created": created},
    )
    session = await issue_session(
        ctx, user, mfa_pending=user.totp_enabled, user_agent=user_agent, method=provider
    )
    return CallbackResult(session, str(data.get("next") or "/app"), created)


async def resolve_user(
    ctx: Ctx, identity: OidcIdentity, fallback_name: str | None = None
) -> tuple[User, bool]:
    """Find the user for an external identity; link by verified e-mail; otherwise create one."""
    now = datetime.now(UTC)
    provider = OAuthProvider(identity.provider)
    link = await ctx.db.scalar(
        select(OAuthIdentity).where(
            OAuthIdentity.provider == provider, OAuthIdentity.subject == identity.subject
        )
    )
    if link is not None:
        link.last_used_at = now
        user = await ctx.db.get(User, link.user_id)
        assert user is not None
        return user, False
    if not identity.email or not identity.email_verified:
        # Without a verified address we cannot link safely or contact the user.
        raise ProblemError(
            400, "oauth-email-unverified", "The provider did not confirm an e-mail address"
        )
    user = await ctx.db.scalar(select(User).where(User.email == identity.email))
    created = user is None
    if user is None:
        user = User(
            email=identity.email,
            name=(identity.name or fallback_name or identity.email.split("@")[0])[:120],
            locale="de-CH",
            password_hash=None,
            email_verified_at=now,
            terms_accepted_at=now,  # the sign-in button states that continuing accepts the terms
        )
        ctx.db.add(user)
        await ctx.db.flush()
        await audit.record(
            ctx,
            "user.registered",
            target_type="user",
            target_id=user.id,
            actor_id=user.id,
            data={"via": identity.provider},
        )
    else:
        user.email_verified_at = user.email_verified_at or now
    ctx.db.add(
        OAuthIdentity(
            user_id=user.id,
            provider=provider,
            subject=identity.subject,
            email=identity.email,
            last_used_at=now,
        )
    )
    await ctx.db.flush()
    return user, created

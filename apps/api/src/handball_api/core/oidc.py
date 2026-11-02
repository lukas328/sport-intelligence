"""OpenID Connect client for Google and Apple sign-in (ADR 010).

Authorization code flow with PKCE (S256), state and nonce. ID tokens are verified against the
provider's JWKS (signature, issuer, audience, expiry, nonce). Endpoints are fixed per provider and
can be overridden by configuration (tests, self-hosted identity providers).
"""

from __future__ import annotations

import base64
import hashlib
import secrets
import time
from dataclasses import dataclass, field, replace
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt

from handball_api.core.config import Settings


class OidcError(Exception):
    pass


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    issuer: str
    authorize_url: str
    token_url: str
    jwks_url: str
    scopes: str
    client_id: str
    response_mode: str | None = None  # Apple: form_post (required when asking for e-mail)
    extra_auth_params: dict[str, str] = field(default_factory=dict)


GOOGLE = {
    "issuer": "https://accounts.google.com",
    "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
    "token_url": "https://oauth2.googleapis.com/token",
    "jwks_url": "https://www.googleapis.com/oauth2/v3/certs",
}
APPLE = {
    "issuer": "https://appleid.apple.com",
    "authorize_url": "https://appleid.apple.com/auth/authorize",
    "token_url": "https://appleid.apple.com/auth/token",
    "jwks_url": "https://appleid.apple.com/auth/keys",
}


def enabled_providers(settings: Settings) -> dict[str, ProviderConfig]:
    out: dict[str, ProviderConfig] = {}
    if settings.google_client_id:
        out["google"] = ProviderConfig(
            name="google",
            scopes="openid email profile",
            client_id=settings.google_client_id,
            extra_auth_params={"prompt": "select_account"},
            **_endpoints(GOOGLE),
        )
    if (
        settings.apple_client_id
        and settings.apple_team_id
        and settings.apple_key_id
        and settings.apple_private_key
    ):
        out["apple"] = ProviderConfig(
            name="apple",
            scopes="name email",
            client_id=settings.apple_client_id,
            response_mode="form_post",
            **_endpoints(APPLE),
        )
    for name, override in settings.oidc_overrides.items():
        if name in out:
            out[name] = replace(out[name], **_endpoints({**_as_dict(out[name]), **override}))
    return out


def _endpoints(d: dict[str, str]) -> dict[str, Any]:
    return {k: d[k] for k in ("issuer", "authorize_url", "token_url", "jwks_url")}


def _as_dict(p: ProviderConfig) -> dict[str, str]:
    return {
        "issuer": p.issuer,
        "authorize_url": p.authorize_url,
        "token_url": p.token_url,
        "jwks_url": p.jwks_url,
    }


def pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    )
    return verifier, challenge


def authorize_url(
    p: ProviderConfig, redirect_uri: str, state: str, nonce: str, challenge: str
) -> str:
    params = {
        "client_id": p.client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": p.scopes,
        "state": state,
        "nonce": nonce,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        **p.extra_auth_params,
    }
    if p.response_mode:
        params["response_mode"] = p.response_mode
    return f"{p.authorize_url}?{urlencode(params)}"


def client_secret(p: ProviderConfig, settings: Settings) -> str:
    if p.name == "google":
        if settings.google_client_secret is None:
            raise OidcError("google client secret missing")
        return settings.google_client_secret.get_secret_value()
    # Apple: the client secret is a short-lived ES256 JWT signed with the team's key.
    assert settings.apple_private_key and settings.apple_team_id and settings.apple_key_id
    now = int(time.time())
    return jwt.encode(
        {
            "iss": settings.apple_team_id,
            "iat": now,
            "exp": now + 300,
            "aud": "https://appleid.apple.com",
            "sub": p.client_id,
        },
        settings.apple_private_key.get_secret_value(),
        algorithm="ES256",
        headers={"kid": settings.apple_key_id},
    )


@dataclass(frozen=True)
class OidcIdentity:
    provider: str
    subject: str
    email: str | None
    email_verified: bool
    name: str | None


class OidcClient:
    """HTTP side of the flow. The httpx client is injectable for tests."""

    def __init__(self, http: httpx.AsyncClient | None = None) -> None:
        self._http = http or httpx.AsyncClient(timeout=10)
        self._jwks: dict[str, tuple[float, dict[str, Any]]] = {}

    async def _keys(self, url: str, refresh: bool = False) -> dict[str, Any]:
        cached = self._jwks.get(url)
        if cached and not refresh and time.monotonic() - cached[0] < 3600:
            return cached[1]
        resp = await self._http.get(url)
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
        self._jwks[url] = (time.monotonic(), data)
        return data

    async def exchange(
        self, p: ProviderConfig, code: str, redirect_uri: str, verifier: str, secret: str
    ) -> str:
        resp = await self._http.post(
            p.token_url,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": p.client_id,
                "client_secret": secret,
                "code_verifier": verifier,
            },
            headers={"accept": "application/json"},
        )
        if resp.status_code != 200:
            raise OidcError(f"token endpoint returned {resp.status_code}")
        token = resp.json().get("id_token")
        if not isinstance(token, str):
            raise OidcError("no id_token in token response")
        return token

    async def verify(self, p: ProviderConfig, id_token: str, nonce: str) -> OidcIdentity:
        try:
            kid = jwt.get_unverified_header(id_token).get("kid")
        except jwt.PyJWTError as exc:
            raise OidcError("malformed id_token") from exc
        key = await self._key_for(p.jwks_url, kid)
        try:
            claims = jwt.decode(
                id_token,
                key=key,
                algorithms=["RS256", "ES256"],
                audience=p.client_id,
                issuer=p.issuer,
                options={"require": ["exp", "iat", "sub", "iss", "aud"]},
                leeway=60,
            )
        except jwt.PyJWTError as exc:
            raise OidcError(f"invalid id_token: {exc}") from exc
        if claims.get("nonce") != nonce:
            raise OidcError("nonce mismatch")
        verified = claims.get("email_verified") in (True, "true")
        return OidcIdentity(
            provider=p.name,
            subject=str(claims["sub"]),
            email=claims.get("email"),
            email_verified=verified,
            name=claims.get("name"),
        )

    async def _key_for(self, url: str, kid: str | None) -> Any:
        for refresh in (False, True):
            for jwk in (await self._keys(url, refresh)).get("keys", []):
                if jwk.get("kid") == kid:
                    return jwt.PyJWK(jwk).key
        raise OidcError("signing key not found")

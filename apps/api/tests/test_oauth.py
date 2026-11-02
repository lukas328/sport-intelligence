"""Sign-in with Google and Apple against a simulated identity provider (real signed ID tokens)."""

from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator, Callable
from typing import Any
from urllib.parse import parse_qs, urlsplit

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from fastapi import FastAPI
from pydantic import SecretStr

from handball_api.core.config import Settings
from handball_api.core.email import MemoryEmailSender
from handball_api.core.jobs import MemoryEventBus, MemoryJobQueue
from handball_api.core.oidc import OidcClient
from handball_api.core.ratelimit import MemoryRateLimiter
from handball_api.core.storage import MemoryStorage
from handball_api.main import create_app

from .conftest import Api

pytestmark = pytest.mark.usefixtures("clean_db")

IDP = "https://idp.test"


class FakeIdp:
    def __init__(self) -> None:
        self.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.claims: dict[str, Any] = {}
        self.nonce = ""
        self.token_requests: list[dict[str, list[str]]] = []

    def jwks(self) -> dict[str, Any]:
        jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(self.key.public_key()))
        return {"keys": [{**jwk, "kid": "k1", "alg": "RS256", "use": "sig"}]}

    def id_token(self, aud: str, iss: str) -> str:
        now = int(time.time())
        claims = {
            "iss": iss,
            "aud": aud,
            "sub": "sub-1",
            "iat": now,
            "exp": now + 300,
            "nonce": self.nonce,
            "email": "ola@hc-test.ch",
            "email_verified": True,
            "name": "Ola Nordmann",
            **self.claims,
        }
        pem = self.key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        return jwt.encode(claims, pem, algorithm="RS256", headers={"kid": "k1"})

    def handler(self, request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/jwks"):
            return httpx.Response(200, json=self.jwks())
        if request.url.path.endswith("/token"):
            form = parse_qs(request.content.decode())
            self.token_requests.append(form)
            provider = "apple" if "apple" in request.url.path else "google"
            aud = form["client_id"][0]
            return httpx.Response(200, json={"id_token": self.id_token(aud, f"{IDP}/{provider}")})
        return httpx.Response(404)


def overrides(provider: str) -> dict[str, str]:
    return {
        "issuer": f"{IDP}/{provider}",
        "authorize_url": f"{IDP}/{provider}/authorize",
        "token_url": f"{IDP}/{provider}/token",
        "jwks_url": f"{IDP}/{provider}/jwks",
    }


@pytest.fixture
def idp() -> FakeIdp:
    return FakeIdp()


@pytest.fixture
async def oauth_app(db_settings: Settings, clean_db: None, idp: FakeIdp) -> AsyncIterator[FastAPI]:
    apple_key = (
        ec.generate_private_key(ec.SECP256R1())
        .private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        .decode()
    )
    settings = db_settings.model_copy(
        update={
            "google_client_id": "google-client",
            "google_client_secret": SecretStr("g-secret"),
            "apple_client_id": "ch.handball.web",
            "apple_team_id": "TEAM1",
            "apple_key_id": "KEY1",
            "apple_private_key": SecretStr(apple_key),
            "oidc_overrides": {"google": overrides("google"), "apple": overrides("apple")},
        }
    )
    oidc = OidcClient(httpx.AsyncClient(transport=httpx.MockTransport(idp.handler)))
    app = create_app(
        settings,
        jobs=MemoryJobQueue(),
        events=MemoryEventBus(),
        email=MemoryEmailSender(),
        storage=MemoryStorage(),
        rate_limiter=MemoryRateLimiter(),
        oidc=oidc,
    )
    async with app.router.lifespan_context(app):
        yield app


async def sign_in(
    api: Api,
    idp: FakeIdp,
    provider: str = "google",
    next_path: str | None = None,
    invite: str | None = None,
) -> httpx.Response:
    params = {k: v for k, v in {"next": next_path, "invite": invite}.items() if v}
    start = await api.get(f"/v1/auth/oauth/{provider}/start", params=params)
    assert start.status_code == 302, start.text
    q = parse_qs(urlsplit(start.headers["location"]).query)
    assert q["code_challenge_method"] == ["S256"]
    idp.nonce = q["nonce"][0]
    if provider == "apple":
        assert q["response_mode"] == ["form_post"]
        return await api.http.post(
            f"/v1/auth/oauth/{provider}/callback",
            data={
                "code": "c",
                "state": q["state"][0],
                "user": json.dumps({"name": {"firstName": "Anna", "lastName": "Apfel"}}),
            },
            headers={"origin": "https://appleid.apple.com"},
        )
    return await api.get(
        f"/v1/auth/oauth/{provider}/callback", params={"code": "c", "state": q["state"][0]}
    )


async def test_providers(oauth_app: FastAPI, make_api: Callable[[], Api]) -> None:
    api = Api(oauth_app)
    assert (await api.get("/v1/auth/providers")).json() == {"providers": ["apple", "google"]}
    plain = make_api()
    assert (await plain.get("/v1/auth/providers")).json() == {"providers": []}
    assert (await plain.get("/v1/auth/oauth/google/start")).status_code == 404


async def test_google_new_user_then_returning(oauth_app: FastAPI, idp: FakeIdp) -> None:
    api = Api(oauth_app)
    r = await sign_in(api, idp)
    assert r.status_code == 303
    assert r.headers["location"] == "http://web.test/onboarding"
    me = (await api.get("/v1/me")).json()
    assert me["email"] == "ola@hc-test.ch"
    assert me["name"] == "Ola Nordmann"
    assert me["has_password"] is False
    assert me["email_verified"] is True
    assert me["linked_providers"] == ["google"]
    # PKCE verifier and secret were sent to the token endpoint
    assert idp.token_requests[-1]["code_verifier"][0]
    assert idp.token_requests[-1]["client_secret"] == ["g-secret"]
    sessions = (await api.get("/v1/me/sessions")).json()
    assert sessions[0]["method"] == "google"

    again = Api(oauth_app)
    r = await sign_in(again, idp, next_path="/app/settings")
    assert r.headers["location"] == "http://web.test/app/settings"
    assert (await again.get("/v1/me")).json()["id"] == me["id"]
    # an OAuth-only account can set a password without the current one
    assert (
        await again.post("/v1/me/password", json={"new_password": "first-password-1"})
    ).status_code == 204


async def test_links_existing_account_by_verified_email(oauth_app: FastAPI, idp: FakeIdp) -> None:
    pw = Api(oauth_app)
    await pw.register("ola@hc-test.ch", name="Ola")
    g = Api(oauth_app)
    r = await sign_in(g, idp)
    assert r.headers["location"] == "http://web.test/app"
    assert (await g.get("/v1/me")).json()["id"] == pw.user["id"]


async def test_unverified_email_is_rejected(oauth_app: FastAPI, idp: FakeIdp) -> None:
    idp.claims = {"email_verified": False}
    r = await sign_in(Api(oauth_app), idp)
    assert r.headers["location"] == "http://web.test/login?error=oauth-email-unverified"


async def test_state_and_nonce_are_checked(oauth_app: FastAPI, idp: FakeIdp) -> None:
    api = Api(oauth_app)
    start = await api.get("/v1/auth/oauth/google/start")
    q = parse_qs(urlsplit(start.headers["location"]).query)
    bad_state = await api.get(
        "/v1/auth/oauth/google/callback", params={"code": "c", "state": "forged"}
    )
    assert bad_state.headers["location"].endswith("error=oauth-state")
    # a failed callback consumes the state cookie: start again
    start = await api.get("/v1/auth/oauth/google/start")
    q = parse_qs(urlsplit(start.headers["location"]).query)
    idp.nonce = "other"
    bad_nonce = await api.get(
        "/v1/auth/oauth/google/callback", params={"code": "c", "state": q["state"][0]}
    )
    assert bad_nonce.headers["location"].endswith("error=oauth-failed")
    no_cookie = Api(oauth_app)
    r = await no_cookie.get(
        "/v1/auth/oauth/google/callback", params={"code": "c", "state": q["state"][0]}
    )
    assert r.headers["location"].endswith("error=oauth-state")
    cancelled = await api.get("/v1/auth/oauth/google/callback", params={"error": "access_denied"})
    assert cancelled.headers["location"].endswith("error=oauth-cancelled")
    assert (await api.get("/v1/me")).status_code == 401


async def test_wrong_audience_rejected(oauth_app: FastAPI, idp: FakeIdp) -> None:
    idp.claims = {"aud": "someone-else"}
    r = await sign_in(Api(oauth_app), idp)
    assert r.headers["location"].endswith("error=oauth-failed")


async def test_open_redirect_blocked(oauth_app: FastAPI, idp: FakeIdp) -> None:
    r = await sign_in(Api(oauth_app), idp, next_path="//evil.example")
    assert r.headers["location"] == "http://web.test/onboarding"


async def test_apple_form_post_with_name(oauth_app: FastAPI, idp: FakeIdp) -> None:
    idp.claims = {"email": "anna@hc-test.ch", "email_verified": "true", "name": None}
    api = Api(oauth_app)
    r = await sign_in(api, idp, provider="apple")
    assert r.status_code == 303, r.text
    me = (await api.get("/v1/me")).json()
    assert me["name"] == "Anna Apfel"
    assert me["linked_providers"] == ["apple"]
    secret = idp.token_requests[-1]["client_secret"][0]
    header = jwt.get_unverified_header(secret)
    assert header["alg"] == "ES256"
    assert header["kid"] == "KEY1"


async def test_google_with_invitation(
    oauth_app: FastAPI, idp: FakeIdp, outbox: MemoryEmailSender
) -> None:
    admin = Api(oauth_app)
    await admin.register("boss@hc-test.ch")
    org = (await admin.post("/v1/orgs", json={"name": "HC OAuth"})).json()["id"]
    team = (
        await admin.post(f"/v1/orgs/{org}/teams", json={"name": "U17", "gender": "men"})
    ).json()["id"]
    await admin.post(
        f"/v1/orgs/{org}/invitations",
        json={"email": "ola@hc-test.ch", "team_id": team, "team_role": "analyst"},
    )
    token = oauth_app.state.email.outbox[-1].text.split("/invite/")[1].split()[0]
    g = Api(oauth_app)
    r = await sign_in(g, idp, invite=token, next_path=f"/app/{org}")
    assert r.headers["location"] == f"http://web.test/app/{org}"
    teams = (await g.get(f"/v1/orgs/{org}/teams")).json()
    assert teams[0]["my_role"] == "analyst"


async def test_totp_users_need_second_factor(oauth_app: FastAPI, idp: FakeIdp) -> None:
    import pyotp

    api = Api(oauth_app)
    await sign_in(api, idp)
    secret = (await api.post("/v1/me/totp/setup")).json()["secret"]
    await api.post("/v1/me/totp/enable", json={"code": pyotp.TOTP(secret).now()})
    fresh = Api(oauth_app)
    r = await sign_in(fresh, idp)
    assert r.headers["location"].startswith("http://web.test/login?totp=1")
    assert (await fresh.get("/v1/me")).status_code == 401

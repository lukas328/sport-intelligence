# 010. Sign-in with Google and Apple (OpenID Connect)

- Status: accepted
- Date: 2026-11-02

## Decision
- Own small OIDC client (`core/oidc.py`, httpx + PyJWT) instead of a framework: authorization code flow
  with **PKCE (S256)**, `state` and `nonce`. ID tokens are verified against the provider JWKS
  (signature RS256/ES256, `iss`, `aud`, `exp`, `nonce`), keys cached 1 h with refresh on unknown `kid`.
- The flow runs on the web origin (`/v1/auth/oauth/{provider}/start` and `/callback`, proxied to the API),
  so the redirect URI is `https://<web>/v1/auth/oauth/<provider>/callback`.
- State, nonce, PKCE verifier, `next` and an optional invitation token live in a signed, 10-minute,
  httpOnly cookie scoped to `/v1/auth/oauth`. A failed callback consumes it.
- Apple: `response_mode=form_post` (required for name/e-mail), so the callback accepts POST, is exempt from
  the Origin check, and the state cookie is `SameSite=None; Secure` in production. The client secret is a
  5-minute ES256 JWT signed with the team key. The name is taken from the first sign-in's `user` field.
- Account resolution: existing link (provider + subject) wins; otherwise link to an existing account
  with the same **verified** e-mail; otherwise create an account (e-mail verified, terms accepted by the
  "continuing accepts the terms" notice). Unverified provider e-mails are rejected.
- TOTP still applies: OIDC sign-in of a user with 2FA yields an `mfa_pending` session.
- A provider is enabled only when configured (`HB_GOOGLE_CLIENT_ID` + secret; `HB_APPLE_*`); the UI asks
  `/v1/auth/providers` and hides buttons otherwise.

## Setup (production)
- Google Cloud Console: OAuth client "Web application", authorised redirect URI
  `https://<domain>/v1/auth/oauth/google/callback`, scopes openid/email/profile.
- Apple Developer: Services ID (= client id), Sign in with Apple key (.p8, key id), team id, return URL
  `https://<domain>/v1/auth/oauth/apple/callback`. Apple requires HTTPS, so it cannot be tested locally.

## Tests
`tests/test_oauth.py` runs both providers against a simulated identity provider with real signed tokens:
new user, returning user, linking by verified e-mail, unverified e-mail, wrong state, wrong nonce, wrong
audience, cancelled flow, open-redirect attempt, Apple form_post with name, invitation acceptance, TOTP.

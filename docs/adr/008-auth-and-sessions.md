# 008. Authentication and sessions

- Status: accepted
- Date: 2026-11-02

## Decision
- **Passwords**: Argon2id (argon2-cffi defaults), rehash on login when parameters change. Minimum 10
  characters, must not contain the e-mail address. No composition rules (NIST SP 800-63B).
- **Sessions**: opaque random token (32 bytes) in an `httpOnly`, `SameSite=Lax` cookie (`Secure` in
  staging/production, enforced at startup). Only the SHA-256 hash is stored (`auth_sessions`), so a
  database leak does not leak sessions. Logout deletes the row. Lifetime 14 days.
- **CSRF**: signed double submit. The readable `hb_csrf` cookie holds `HMAC(secret, session token)`; every
  unsafe request with a session cookie must echo it in `X-CSRF-Token`. Additionally every unsafe request
  with an `Origin` header must come from an allowed origin.
- **Magic link**: single-use token (hash stored), 15 minutes, always answers 202 (no account enumeration).
- **TOTP (RFC 6238)**: secret encrypted with Fernet (`HB_ENCRYPTION_KEY`). With TOTP enabled, the password
  or magic-link step yields a short-lived session with `mfa_pending`, which only allows the TOTP step.
  Org admins must enable TOTP for org-level write actions after a grace period (default 14 days) so
  onboarding stays under 5 minutes.
- **Invitations**: opaque token (hash stored), 14 days, bound to the invited e-mail address.
- **Rate limits**: Redis fixed window per IP on register, login, TOTP and magic-link endpoints.
- **Browser access** goes through the web origin (`/v1/*` proxied by Next.js), so cookies are first-party
  and the CSP keeps `connect-src 'self'`. The proxy forwards `X-Forwarded-For`; the API trusts it only
  from the internal network (`FORWARDED_ALLOW_IPS`).
- Google and Apple sign-in are optional per brief and postponed (OPEN_QUESTIONS Q-AUTH-1).

## Consequences
Server-side sessions can be revoked instantly and listed per user later (security page). Each request
costs one indexed lookup, which is acceptable.

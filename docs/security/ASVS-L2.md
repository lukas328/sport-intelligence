# Security review against OWASP ASVS 4.0.3 Level 2 (M9)

Date: 2026-11-03 · Scope: API, web app, workers, local infrastructure · Method: requirement-by-requirement
review of the code and configuration, plus automated checks in CI (Trivy for images and dependencies,
policy matrix test, tenant isolation test, axe for accessibility). Status: ✅ met · ◐ partly · ✗ open ·
n/a not applicable. Findings fixed during the review are marked **fixed in M9**.

| Area | Status | Evidence / notes |
|---|---|---|
| V1 Architecture | ✅ | Layer contracts enforced by import-linter; tenant isolation by Postgres RLS with a non-superuser app role (ADR 005); threat surface: web origin, API, internal worker callbacks (shared token), public share links, Stripe webhooks |
| V2.1 Password security | ✅ | min. 10 characters, max. 200, no e-mail inside, common-password list, **breach check via HIBP range API (fixed in M9, `HB_PWNED_CHECK`)**; no composition rules, paste allowed |
| V2.2 Authenticator lifecycle / anti-automation | ✅ | Redis rate limits on login, register, reset, magic link, TOTP, verify, share links; generic errors on login and reset |
| V2.4 Credential storage | ✅ | Argon2id with rehash on login |
| V2.5 Recovery | ✅ | single-use hashed tokens, 60 min, all sessions revoked after reset |
| V2.7/2.8 OTP / TOTP | ✅ | TOTP (RFC 6238) with encrypted secrets (Fernet), required for org admins after the grace period and for operators in production; ten one-time recovery codes stored as HMAC (**added after M9**) |
| V3 Session management | ✅ | opaque random tokens, only SHA-256 stored, httpOnly + Secure + SameSite=Lax cookies, 14 day expiry, logout and "sign out other devices", device list |
| V4 Access control | ✅ | central policy table, generated matrix (docs/policy-matrix.md), policy matrix test over every endpoint × 7 roles, deny by default, RLS as second line, operator backoffice invisible (404) |
| V5 Validation, sanitisation, encoding | ✅ | Pydantic schemas with limits on every input, React escaping, CSP without `unsafe-eval` in production, SSRF guard for link imports (public HTTPS only, redirects re-checked), path traversal checks on media paths |
| V6 Cryptography | ✅ | `secrets` tokens, HMAC-signed CSRF and OAuth state, Fernet for TOTP secrets, no custom crypto |
| V7 Errors and logging | ✅ | RFC 9457 problems without stack traces, structured JSON logs with request ids, audit log for security events and every RLS bypass, no secrets in logs |
| V8 Data protection | ✅ | **`Cache-Control: no-store` on all API data (fixed in M9)**, data minimisation in shared links (numbers, no names), personal data export and deletion (M9), youth defaults |
| V9 Communications | ◐ | HSTS when served over HTTPS (**fixed in M9**); TLS termination and cipher policy belong to the hosting load balancer (GO_LIVE) |
| V10 Malicious code | ✅ | pinned lockfiles, Trivy on every image in CI (HIGH/CRITICAL fail), GitHub Actions pinned by SHA |
| V11 Business logic | ✅ | plan limits server-side, idempotent Stripe webhooks, single retry per failed job |
| V12 Files and resources | ✅ | uploads go directly to object storage with presigned parts, size limits, extension and magic-byte checks (logos), no user-controlled paths, media served only through authorised endpoints |
| V13 API | ✅ | CSRF double submit + Origin check for cookie sessions, strict CORS, JSON only, webhook signatures verified |
| V14 Configuration | ✅ | refuses to start in staging/production with development secrets or insecure cookies, **no server banner (fixed in M9)**, security headers (CSP, X-Frame-Options, nosniff, Referrer-Policy, Permissions-Policy) |

## Open items before go-live
- External penetration test of the deployed staging environment (GO_LIVE.md).
- TLS configuration of the chosen hosting (Q-INFRA-1).
- Turn on `HB_PWNED_CHECK=true` and `HB_BILLING_ENFORCE=true` in production.

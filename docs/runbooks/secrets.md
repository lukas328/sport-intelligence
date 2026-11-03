# Rotate secrets

| Secret | Effect of rotation | How |
|---|---|---|
| `HB_SECRET_KEY` (CSRF/OAuth state signing) | open forms and OAuth flows fail once | set new value, restart API |
| `HB_ENCRYPTION_KEY` (TOTP secrets) | none if done in order | comma-separated key list: set `new,old`, deploy, run `python -m handball_api.rotate_keys` (re-encrypts every TOTP secret, idempotent, exit 1 if a secret matches no key), then set `new` only and deploy again |
| `HB_INTERNAL_TOKEN` | worker callbacks fail until all services restart | set in API and workers together, rolling restart |
| `HB_S3_*` | uploads and media fail until restart | create new key, deploy, revoke old key |
| `HB_STRIPE_*` | billing unavailable until restart | roll in the Stripe dashboard, deploy, verify a webhook |
| `HB_ANTHROPIC_API_KEY` | summaries fall back to templates | replace, restart API |
| OIDC client secrets | sign-in with Google/Apple fails until restart | rotate at the provider, deploy |

After every rotation: check `/readyz`, sign in, upload a short clip, receive a webhook (Stripe test event).

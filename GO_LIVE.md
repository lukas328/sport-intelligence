# Go-live checklist

Status of the platform at the end of M9 and what has to happen before real clubs use it.
✅ done in the repository · ☐ to do at go-live (needs an owner decision, an account or the real environment).

## Product
- ✅ Clubs, teams, roster, invitations, roles, consents; sign-in with password, magic link, Google, Apple, TOTP
- ✅ Upload (resumable), processing, HLS player, comments, clips, playlists, drawings
- ✅ Tagging, match report, shots, goalkeepers, insights, season, opponents, plays, assignments, notifications
- ✅ Video analysis baseline (calibration, detection, tracking, teams, physical load, formations): **estimates**,
  labelled in the UI; trained models are the next quality step (ADR 012, Q-ML-2)
- ☐ Validate the analysis on the club's real videos (Q-DATA-1) and adjust filming guidance

## Infrastructure (ADR 002, Q-INFRA-1)
- ✅ Object storage decided: Cloudflare R2 with EU jurisdiction (ADR 002); test-data bucket via `scripts/testdata.py`
- ☐ Choose app hosting in the EU, managed Postgres with PITR, S3-compatible storage with versioning, GPU provider with DPA
- ☐ Terraform module for the chosen provider (`infra/terraform`)
- ☐ TLS on the load balancer, HSTS preload decision, CDN for HLS segments
- ☐ Off-site backup bucket with object lock; schedule `backup.sh`; first production restore test recorded

## Configuration (production)
- ☐ `HB_ENV=production`, strong `HB_SECRET_KEY`, `HB_ENCRYPTION_KEY`, `HB_INTERNAL_TOKEN` (the API refuses dev secrets)
- ☐ `HB_COOKIE_SECURE=true`, `HB_CORS_ORIGINS`, `HB_WEB_BASE_URL`, `HB_S3_PUBLIC_URL`
- ☐ `HB_BILLING_ENFORCE=true`, Stripe keys, webhook secret and price ids (Q-BILL-1); live test purchase in test mode
- ☐ `HB_PWNED_CHECK=true`
- ☐ E-mail provider with SPF, DKIM, DMARC (ADR 009)
- ☐ `HB_OPERATOR_EMAILS` (named people, 2FA enforced), `HB_SENTRY_DSN`, `HB_OTEL_ENDPOINT`
- ☐ Optional `HB_ANTHROPIC_API_KEY` for prose summaries (DPA with the provider, no names are sent)

## Security and privacy
- ✅ ASVS L2 review (`docs/security/ASVS-L2.md`), tenant isolation and policy matrix tests, image scans
- ✅ Personal data export, account and club deletion, youth defaults, shared links without names
- ☐ External penetration test on staging
- ✅ TOTP recovery codes
- ✅ Key rotation for `HB_ENCRYPTION_KEY` (key list, `python -m handball_api.rotate_keys`)
- ☐ Privacy policy, terms, DPA template for clubs (controller) and sub-processor list; records of processing
- ☐ Data protection impact assessment for video of minors

## Operations
- ✅ Runbooks (`docs/runbooks`), restore test script, load test (`docs/perf/load-m9.md`), alert list (`infra/monitoring/alerts.md`)
- ☐ Configure probes and alerts in the chosen monitoring, on-call rota, status page
- ☐ Support mailbox and response times

## Launch
- ☐ Pilot with 2 to 3 clubs for 4 weeks (feedback loop on tagging speed, analysis quality, mobile use)
- ☐ Go/no-go review: open incidents, error rate, p95, backup and restore evidence

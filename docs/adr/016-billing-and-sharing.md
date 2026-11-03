# 016. Billing enforcement and public share links

- Status: accepted
- Date: 2026-11-03

## Context
BRIEF 13 defines Free, Team and Club plans with a goalkeeper add-on, a 30-day trial, central feature flags
and visible usage. The same code runs self-hosted, in CI and in production. Share links must let parents
or players without an account watch content without leaking personal data.

## Decision
- One plan catalogue (`services/plans.py`) with limits (teams, matches per season, storage, GPU minutes)
  and feature flags. `HB_BILLING_ENFORCE` turns enforcement on (production); otherwise everything is
  allowed, so development, CI and self-hosted installs are never blocked.
- Limits return RFC 9457 problems `plan-limit-<limit>` (402), missing features `plan-required` (402); a
  plan without tracking still processes videos (playable) but starts no analysis.
- Stripe Checkout and the customer portal behind a small gateway interface; prices come from config.
  Webhooks are verified with the Stripe signature and processed once per event id (`stripe_events`).
  The subscription is the source of truth for plan, status, trial end, period end and goalkeeper seats;
  a lapsed subscription falls back to Free.
- Share links: random token, only the SHA-256 hash stored, 1 to 90 days, revocable, view count. Public
  endpoints resolve the token with an explicit RLS bypass and then work inside the tenant. Media is
  served only for videos behind the shared content. Shared content shows jersey numbers, never names;
  youth teams share no player rows.

## Consequences
- Plan changes are a code change plus Stripe prices, reviewed like any other change.
- Webhook delivery order does not matter (each event sets absolute state).

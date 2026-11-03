# 018. Partner adapters, support chat and status page

- Status: accepted
- Date: 2026-11-03

## Context
Addendum 01 section 7 asks for adapters instead of own builds for video sources, livestream, team
organisation, official match data, wearables, support chat and the status page. Concrete partner
connections need contracts; until then the product must not depend on them (P10: few, good integrations).

## Decision
- Package `handball_api.integrations` (layer between services and schemas, see import-linter): plain
  Python, no database or HTTP session state. Services call adapters and store results.
- One `Protocol` per category plus a first real implementation where it needs no partner:
  - Video sources: https file link (own files) and YouTube links. YouTube downloads only through the
    owner's own connection (YouTube Data API, OAuth); no ripping, no bypassing terms of service.
    Stubs: Veo, Spiideo, asport, Hudl.
  - Livestream: stub only (no own livestream, non-goal).
  - Team organisation: ICS import/export (RFC 5545 subset: unfolding/folding, escaping, TZID, all-day).
    Stubs: Spond, ClubCorner.
  - Official match data: CSV and JSON feed parsers; stub handball.ch.
  - Wearables: CSV import (position checked against the 40 × 20 m court); stubs Kinexon, Polar.
    Only what the load view needs (health data minimised).
- Stubs raise `NotConfiguredError(partner)`; the registry lists all adapters per category.
- **Support chat: Crisp** (EU hosting, DPA, small price, widget only). Intercom is stronger in automation
  but costlier and US-centred. Only a pseudonymous user hash is passed, never the e-mail address.
- **Status page: hosted external provider** (e.g. Instatus or Better Stack, both with API), independent
  of our hosting; the API reports component state derived from `/health/ready` checks
  (database and storage down = "down", others = "degraded").

## Consequences
- Adding a partner means implementing the protocol and a contract test; no schema or service change.
- Provider accounts (Crisp website id, status page URL and token) are configuration; without them the
  `none` adapters are used and the UI hides the widget or link.

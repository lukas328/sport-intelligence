# Partner integrations

Adapters live in `apps/api/src/handball_api/integrations/` (ADR 018). Each category has a protocol, a
first implementation that needs no partner contract, and stubs for partners. Stubs raise
`NotConfiguredError` until a partnership and credentials exist.

| Category | Protocol | Working now | Stubs |
|---|---|---|---|
| Video sources | `VideoSourceAdapter` (list, metadata, download URL, webhook) | `file_link` (https, own files), `youtube` (links; download only by the owner's own connection) | `veo`, `spiideo`, `asport`, `hudl` |
| Livestream | `StreamPartnerAdapter` (assign match, fetch recording) | none | `stream_partner` |
| Calendar and team | `TeamOpsAdapter` (import, export) | `ics` (RFC 5545 subset) | `spond`, `clubcorner` |
| Official data | `OfficialMatchFeed` (events) | `csv`, `json` | `handball_ch` |
| Sensors | `WearableAdapter` (samples) | `csv` (t_ms, number, x, y, heart_rate, load) | `kinexon`, `polar` |
| Support | `SupportChatAdapter` (widget config) | `crisp`, `none` | |
| Status | `StatusPageAdapter` (public URL, component report) | `external`, `none` | |

Lookup: `handball_api.integrations.adapter("team_ops", "ics")`.

## Formats

**Official feed CSV** (comma, semicolon or tab): `period, clock (mm:ss), team (own|opponent), event,
number`. Events: `goal, miss, save, 7m_goal, 7m_miss, 2min, yellow, red, timeout`. JSON: a list of the
same objects or `{"events": [...]}`.

**Wearable CSV**: `t_ms` and `number` are required; `x` (0 to 40 m), `y` (0 to 20 m), `heart_rate`,
`load` are optional. Decimal comma is accepted.

## Export API (P2 preparation)
`GET /v1/orgs/{org}/matches/{match}/exports/shots` (staff with video work rights): shots with side,
shooter number (opponents by number only), position, shot and goal zone, outcome, release time in the
main video and the matching time in each goal camera (`format_version` 1). Intended for the separate
goalkeeper anticipation trainer.

## Testing
`apps/api/tests/test_integrations.py` covers parsers, round trips, validation and that every stub raises
`NotConfiguredError`.

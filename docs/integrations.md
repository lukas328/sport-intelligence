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

**Official match report by link** (`services/official_report.py`, not an adapter: public data, no
contract): `POST /v1/orgs/{org}/matches/{match}/official-report` with `{"url": "..."}` (coach, analyst).
A handball.ch match centre link (`.../matchcenter/spiele/<id>`, GraphQL game log) or a DHB press report
(`dhbdata.fmp.sportradar.com/match/<id>/pressReport.pdf`, read with `pdftotext`, poppler-utils in the API
image); a plain id needs `"provider": "handball_ch" | "dhb"`. Only these fixed hosts are fetched (15 s
timeout). Goals with scorer and shirt number, 7 m, shots and saves (handball.ch), technical errors,
warnings, suspensions, disqualifications and time-outs become events with source `official_report`;
a re-import replaces them. Goals already stored on the same side within 20 s of match clock: a goal a
person entered wins (no official duplicate); an automatic goal (overlay, heuristic) is merged into the
official goal, which keeps its video time and position (`attributes.video`). Overlay goals without an
official counterpart stay, so the video reading can be checked against the report; a later analysis
drops overlay goals next to official ones and estimates no goals. Errors: 422 `report-url-unsupported`,
404 `report-not-found`, 422 `report-unreadable` / `report-empty`, 502/503 `report-unavailable`.

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

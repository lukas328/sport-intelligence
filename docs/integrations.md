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
Sources (sources and terms: `docs/plans/data-sources-de.md`):

| Provider | Link the coach pastes | What is read |
|---|---|---|
| `handball_ch` | `www.handball.ch/de/matchcenter/spiele/<id>` | GraphQL game log: goals, shots, saves, technical errors, cards, suspensions, time-outs |
| `dhb` | `dhbdata.fmp.sportradar.com/match/<id>/pressReport.pdf` (3. Liga, JBLH) | PDF log: goals, 7 m, warnings, suspensions, disqualifications, time-outs |
| `nuliga` | `<association>-handball.liga.nu/cgi-bin/WebObjects/nuLigaHBDE.woa/wa/groupMeetingReport?meeting=<id>&championship=<name>&group=<id>` (BHV, HHV, HVNB, HVS, HVSA, THV, HVMV, MHV; Austria: `oehb-handball.liga.nu/…/nuLigaHBAT.woa/…`), or the PDF `…/nuLigaDokumentHB(DE\|AT).woa/wa/nuDokument?dokument=meetingReportHB&meeting=<id>` (the link on oehb.at, also used when the page link has no championship) | Teams, result and half-time, rosters, the log "Spielverlauf": goals and 7 m (scored / missed) with time, score, shirt number and scorer, 2 minutes, warnings, disqualifications, time-outs. Cards and 2 minutes come from the roster columns when the log does not list them |
| `hla` | `infographics.sportradar.com/hla/pageSnapshot/pdf/de/<id>` (HLA Meisterliga / Challenge) | Teams, result, half-time and the missed 7 m with time and shooter. This report has no timed log of the goals: the import adds a warning pointing to the ÖHB nuLiga report of the game |

PDFs are read with `pdftotext` (poppler-utils in the API image). A plain id needs `"provider":
"handball_ch" | "dhb" | "hla"`; nuLiga needs the link (it names the association). Only these hosts are
fetched: the fixed ones and, for nuLiga, any `<name>-handball.liga.nu`; the URL fetched is rebuilt from
the checked parts of the link (meeting, championship, group), redirects are followed on the same host
only, and no other link is followed. One request per import, only when a coach asks (15 s timeout,
5 MB PDF / 2 MB page limit); nothing is crawled or synced from nuLiga or Sportradar. Everything becomes
events with source `official_report`; a re-import replaces them. Goals already stored on the same side within 20 s of match clock: a goal a
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

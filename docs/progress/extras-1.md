# After M9: extras (1)

Date: 2026-11-03

| Feature | What | Tests |
|---|---|---|
| TOTP recovery codes | ten one-time codes (HMAC stored), shown at activation, regenerate with a TOTP code, count in the settings; login accepts app or recovery codes | API (single use, case and dash tolerant, regeneration replaces), Playwright (sign in with a recovery code) |
| Performance budgets in CI | first-load JS per route (start page ≤ 250 kB, others ≤ 300 kB gzip); LCP and CLS of public pages with 4x CPU throttling (`docs/perf/web-vitals.md`) | budget script in CI, Playwright perf spec |
| Live tagging (courtside) | phone/tablet page per match: running clock with halves, big buttons for our players and the opponent, 7 m flag, undo, log; events queued in the browser and synced when the hall Wi-Fi is back; installable (manifest, icons), service worker serves the page offline | API (idempotent client ids incl. concurrent retries), Vitest (queue order, offline stop, invalid events dropped, clock), Playwright (offline, reload offline, sync on reconnect) |

Live events carry the match clock; setting the kickoff marks in the video view later aligns them with
the video (M4).

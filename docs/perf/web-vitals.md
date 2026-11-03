# Web performance budgets

BRIEF 7.3: LCP < 2.5 s, INP < 200 ms, first-load JS of the start page < 250 kB gzip.

| Check | Where | Result (2026-11-03) |
|---|---|---|
| First-load JS per route (gzip) | `pnpm --filter @handball/web budget` in CI after the build; start page ≤ 250 kB, every route ≤ 300 kB | start page 106 kB; heaviest route (match page with player, tagger, analysis) 174 kB |
| LCP and CLS of public pages | `e2e/perf.spec.ts` (Chromium, 4x CPU throttling) | `/` 408 ms, `/login` 260 ms, `/register` 236 ms; CLS 0 |

Heavy parts are loaded on demand: hls.js only in the player, QR code only during 2FA setup, the tactics
board only on play pages. INP is not measured automatically yet; interactions that touch many elements
(timeline scrubbing, mini court) run outside React renders (canvas, refs).

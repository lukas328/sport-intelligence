# UX: UI-first redesign, report

Date: 2026-11-03 · Status: **done for the web app and the marketing site**; the Expo app took over
the colours; usability sessions with real people are open (Q-UX-1)

## Starting point
Eleven milestones had added one menu entry per feature: 10 links in the club navigation, 11 team
tabs, 8 match tabs and 6 action buttons on the match page, the team opening on a roster form, a
narrow column on every page, system font, bordered boxes, 21 symbol characters as controls,
`window.confirm`, no loading or error states, no theme switch, club colours unreadable on the dark
theme (#003366 at 1.49:1). On a phone the navigation took four rows before any content.

## Delivered
| Area | Result |
|---|---|
| Navigation | At most four destinations per role (coach Übersicht · Spiele · Team · Training; player Übersicht · Szenen · Termine · Team; parent Übersicht · Termine · Team), sidebar on desktop, tab bar on phones, two levels at most, team switcher, account menu (profile, consents, settings, appearance, help, feedback, sign out), command palette ⌘K with destinations, actions, matches and a direct question to the data assistant. Old URLs unchanged |
| Übersicht | Coach: next match with "Vorbereiten" and "Live erfassen", last match with scoreboard, analysis state and the three strongest insights (P2: from the insight engine, with roster names), "Frag deine Daten", next training. Player and parent: next dates with yes / no, open assignments, new scenes. First steps: one next step, the rest folded, can be hidden |
| Spiel | Scoreboard header; three views (Video · Analyse · Szenen) instead of eight tabs; one primary action depending on state (Live erfassen before the match, Video hochladen without video); everything else in "…" (PDF, live, marks, scouting, opponent, data exchange, edit, delete with a confirm dialog); processing as one progress card; edit and data exchange in dialogs |
| Spiele | Upcoming and played, date block, state and result per row; new match in a dialog with home / away and kit swatches; the first match is created inline; score sheet photo and file import next to it |
| Team | Kader (jersey badges, add and CSV import in dialogs), Saison with Matrix and "Frag deine Daten" as actions, Bibliothek (playlists, plays, presentations, scene search) |
| Training | Planung · Termine · Übungen · Aufgaben under one header |
| Settings | Section navigation (sticky on desktop) |
| Tools | Live tagging, marks, presenter and remote full screen with one close button |
| States | `loading`, `error` and `not-found` for the app, skeletons, empty states that say what to do next |
| Visual language | Archivo variable (weight and width, self-hosted, SIL OFL), wide headings and scoreboard figures; paper and ink tokens; club colour per theme at 4.5:1 (`lib/color.ts`); dark mode with a switch and no flash; lucide icons; own primitives on Radix and cmdk; product mark |
| Public pages | Start page, sign-in, registration and onboarding in the same language; marketing site with the same tokens, typeface and mark; help articles updated to the new paths (de, fr, en) |
| Expo app | Same colour tokens (typeface with the first device build, Q-UX-2) |
| Docs | `docs/DESIGN.md`, ADR 023 |

## Measurements
- First-load JavaScript (gzip): start page 150 kB (budget 250), largest route, the match page,
  227 kB (budget 300), team home 186 kB.
- Contrast: every club colour in the tests (yellow, navy, red, white, black, green) reaches 4.5:1 on
  both themes after the shift (`lib.test.ts`).
- Navigation: the club navigation went from 10 links plus 11 team tabs to 4 destinations; the match
  page from 8 tabs and 6 buttons to 3 views, 1 to 2 buttons and a menu.

## Tests
- New: `nav-model.test.ts` (four destinations per role, active destination per path),
  `design-lint.test.ts` (no browser dialogs, no symbol controls, colours from tokens, no long
  dashes, no ß), club colour contrast in both themes.
- Playwright flows updated to the new paths (helpers `openTeam`, `openLibrary`, `openAnalysis`,
  `matchMenu`, `follow`); axe checks unchanged and green.
- Results: Vitest all packages green (web 56), Playwright 31 passed and 19 skipped (desktop-only
  flows in the mobile project), axe without findings. Two earlier full runs showed a link click
  lost while the previous route was still streaming under full CPU load; the flows now wait for
  the URL and retry once (`follow`). One run failed because the local disk was full (S3 refused
  writes), not because of the app.

## Not done / open
- Usability sessions with coaches, players and parents (Q-UX-1).
- Archivo in the Expo app (Q-UX-2); the app's screens keep their layout.
- Pages with little traffic (ops back office, federation pages, public profile) took over the new
  components and tokens but were not reworked screen by screen.

## Vision-Check
- P1 Automatisch zuerst: eingehalten. The start page shows what the analysis produced; upload is the
  one action when a video is missing, everything else follows on its own.
- P2 Jede Zahl führt zum Video: eingehalten. Insights on the start page lead to the match; in the
  analysis every figure still opens its scenes and jumps into the video.
- P3 Ehrlich statt beeindruckend: eingehalten. Demo, heuristic quality checks and processing states
  are labelled; no figures were added that the data does not carry.
- P4 Amateur zuerst: eingehalten. Four places to go, big touch targets, a tab bar on the phone,
  courtside tools full screen.
- P5 Team-Plattform, Torhüter als Modul: eingehalten. Goalkeepers sit inside the analysis next to
  shots and running, not in a separate area.
- P6 Nachwuchs schützen: eingehalten. Parents get their own minimal navigation; nothing about
  visibility or consent changed.
- P7 Datenschutz als Standard: eingehalten. The font is self-hosted (no request to a font service);
  the theme and team choices are first-party cookies.
- P8 Handball-Sprache: eingehalten. Scoreboard, jersey numbers and court as the visual identity;
  texts in de-CH, fr, en.
- P9 Partner statt alles selbst: eingehalten. Radix, cmdk and lucide instead of own widgets.
- P10 Schnell und günstig: eingehalten. Within the route budgets, no new servers.

## Second pass (same day, owner feedback)
- "Heute" is now "Übersicht" in all three languages.
- The desktop sidebar unfolds the second level under the active destination (Kader, Saison,
  Bibliothek; Planung, Termine, Übungen, Aufgaben) and shows the next match; the pill row is
  phone only.
- Library rebuilt around the team's content (plays as board previews, playlists and
  presentations as lists, scene search as the first entry) instead of four icon tiles.
- Generic patterns removed: uppercase micro labels, tinted icon squares on the start page.
- Analysis: goal with red and white posts and a neutral ink scale, toggles as quiet chips, score
  flow with a legend and labelled line ends, insights name "your goalkeeper" instead of "?" when no
  player is assigned, status badge only while uploading, processing or failed.

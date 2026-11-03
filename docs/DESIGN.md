# Design

How the web app looks and behaves, and why. The rules below are checked where possible
(`apps/web/src/lib/design-lint.test.ts`, `apps/web/src/lib/nav-model.test.ts`). ADR 023 records
the decisions; this file is the working reference.

## Principles

1. **One question per screen.** Every page answers one thing ("What is next?", "How did we
   play?", "Who is in the squad?"). Anything else is one click away, not on the page.
2. **One primary action at most.** It changes with the state: before a match "Live erfassen",
   without a video "Video hochladen", afterwards nothing shouts. The rest sits in the "…" menu.
3. **State before features.** Empty, loading, processing and error states say what is going on
   and what to do next. No bare "no data", no spinner without context.
4. **Every number leads to the video** (P2). Figures are buttons or links to the scenes behind
   them, wherever the data allows it.
5. **Honest** (P3). Estimates, heuristics and demo data are labelled as such, in plain words.
6. **Quiet chrome, loud content.** Navigation and controls are neutral; the score, the video and
   the court are the loudest things on screen.

## Navigation

At most **four destinations per role** (main navigation: sidebar on desktop, tab bar on phones).

| Role | Destinations |
|---|---|
| Coach, analyst, team manager, admin | Heute · Spiele · Team · Training |
| Player, goalkeeper | Heute · Szenen · Termine · Team |
| Parent | Heute · Termine · Team |
| Guest | Heute · Spiele · Team |

- Second level (pill links under the title, never more than four): Team → Kader · Saison ·
  Bibliothek; Training → Planung · Termine · Übungen · Aufgaben. There is no third level: pages
  below (Matrix, Frag deine Daten, Playlists, Spielzüge, Präsentationen, Szenensuche) show a back
  link to their parent.
- Account menu (avatar): Profil, Einwilligungen, Einstellungen, Darstellung (hell, dunkel,
  automatisch), Hilfe, Feedback, Abmelden.
- Team switcher in the sidebar or top bar; every team page follows the active team (cookie
  `hb_team`), a match page switches it to the match's team.
- Command palette (⌘K / Ctrl K, search icon on phones): destinations, actions (new match, ask the
  data, search scenes, photograph a sheet), the team's matches, other teams. A typed question
  goes straight to the data assistant.
- Courtside and presentation tools (`/live`, `/marks`, `/present`, `/remote`) run full screen
  with a single close button.

## Key screens

- **Heute** (coach): next match with "Vorbereiten" and "Live erfassen"; last match with score,
  analysis state and the three strongest insights; "Frag deine Daten"; next training. The first
  steps checklist shows one next step and folds the rest; it can be hidden.
- **Heute** (player, parent): next dates with yes / no reply, open assignments, new scenes.
- **Spiel**: scoreboard header, three views (Video · Analyse · Szenen). Analyse holds Übersicht,
  Würfe, Torhüter, Laufleistung and Matchreport. Upload sits in the video view while there is no
  video; processing shows as one progress card. PDF, live, marks, scouting, opponent, data
  exchange, edit and delete live in the "…" menu.
- **Spiele**: upcoming and played, each row with date block, opponent, state and result. A new
  match opens in a dialog; the first match is created inline.

## Visual language

- **Typeface:** Archivo (SIL OFL, self-hosted, `src/fonts`), one variable family with weight
  and width axes. Headings and scores use the wide cut (`font-stretch: 112 %`, scores 118 % and
  800 weight, tabular figures); text uses the normal width. Size steps: 0.6875 (eyebrow),
  0.8125, 0.9375 (body), 1.125, 1.75, 2.25 rem.
- **Colour:** paper and ink. Page `#f7f7f4`, panels white, text `#121411`; dark theme
  `#0d0e0c` / `#161815` / `#edeee9`. One accent: the club colour, shifted per theme until it
  reaches 4.5:1 on the page (`lib/color.ts`, `clubStyle`); the raw club colour is used only for
  decoration (logo tile, a stripe). Green and red mean goal / no goal and ok / error, nothing
  else. Tokens live in `globals.css`; only files that draw courts, kits or overlays may name
  colours.
- **Surfaces:** white panels with a hairline ring (`ring-1 ring-border/70`), radius 16 px for
  panels, 12 px for inputs, pills for buttons and segmented controls. No card inside a card, no
  shadows except on floating layers (menus, dialogs).
- **Icons:** lucide, 1.5 to 2 px stroke, 16 to 24 px. No emoji or symbol characters as controls.
- **Motion:** 150 to 220 ms, ease-out; only where it shows a relation (menus, dialogs, hover
  shifts). `prefers-reduced-motion` turns it off.
- **Domain elements:** `Scoreboard`, `Jersey`, stat tiles with scoreboard figures, the court.

## Components

`components/ui`: `Button` / `buttonClass`, `Card`, `Section`, `Alert`, `EmptyState`, `Skeleton`,
`Badge`, `Segmented` (tabs with arrow keys), `Dialog` (sheet on phones), `Menu*`, `useConfirm`
(instead of `window.confirm`), `PageHeader`, form fields.
`components/shell`: `AppShell`, `TeamSwitcher`, `AccountMenu`, `CommandPalette`, `SubNav`,
`TeamHeader`, `TrainingHeader`.

## Writing

- de-CH without ß, fr, en. No long dashes. Short sentences, verbs on buttons ("Spiel anlegen").
- Say what happens next ("Lade das Video hoch. Statistik, Szenen und Erkenntnisse entstehen danach
  automatisch."), not what is missing.

## Accessibility and performance

WCAG 2.2 AA (axe in every Playwright flow), focus ring in the accent colour, skip link, 44 px
touch targets in the tab bar, no horizontal scrolling at 390 px. Budgets: start page under
250 kB first-load JavaScript, other routes under 300 kB, LCP under 2.5 s with 4x CPU throttling.

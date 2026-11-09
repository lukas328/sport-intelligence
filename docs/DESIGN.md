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
| Coach, analyst, team manager, admin | Übersicht · Spiele · Training · Team |
| Player, goalkeeper | Übersicht · Szenen · Termine · Team |
| Parent | Übersicht · Termine · Team |
| Guest | Übersicht · Spiele · Team |

- Order for staff follows the coach's week: the match, its analysis, the training, then the squad.
- Second level, never more than four, grouped by the job: Spiele → Spielplan · Saison · Bibliothek
  (playlists, presentations, scene search: material from the matches); Training → Planung ·
  Übungen · Spielzüge · Aufgaben; Team → Kader · Termine (the people and when they meet). For
  players, parents and guests Team → Kader · Saison. On desktop the second level unfolds in the
  sidebar under the active destination; on phones it is a row of links under the title. There is
  no third level: pages below (Playlists, Präsentationen, Szenensuche) show a back link to their
  parent; Matrix and Frag deine Daten are tools on the season page.
- The sidebar also shows the next match of the active team.
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

- **Übersicht** (coach): a stage with the next match when it is close (time, opponent, prepare, live), otherwise the last result and its statement; below: next match with "Vorbereiten" and "Live erfassen"; last match with score,
  analysis state and the three strongest insights; "Frag deine Daten"; next training. The first
  steps checklist shows one next step and folds the rest; it can be hidden.
- **Übersicht** (player, parent): next dates with yes / no reply, open assignments, new scenes.
- **Spiel**: scoreboard header, three views (Video · Analyse · Szenen). Analyse holds Übersicht,
  Würfe, Torhüter, Laufleistung and Matchreport. Upload sits in the video view while there is no
  video; processing shows as one progress card. PDF, live, marks, scouting, opponent, data
  exchange, edit and delete live in the "…" menu.
- **Spiele**: upcoming and played, each row with date block, opponent, state and result. A new
  match opens in a dialog; the first match is created inline.

## Identity: "Die Halle" (ADR 024)

The app should feel like a club's hall, not like a dashboard. Two modes, one rule:

| Mode | Purpose | Where | Character |
|---|---|---|---|
| Stage (Bühne) | one moment, one statement | top of Übersicht, Saison, Spiel; landing, sign-in, onboarding | the raw club colour full bleed, court lines from the real geometry, big scoreboard figures, a statement from the data |
| Workbench (Werkbank) | concentrated work | tables, video workspace, tactics, forms, settings | calm: hairlines, paper, clear figures, the match-sheet table |

At most one stage per screen, always at the top; settings and forms never get one. The match
header is a compact stage (scoreboard rows: team, goals); the video workspace below stays calm.

## Visual language

- **Typeface:** Barlow and Barlow Condensed (SIL OFL, self-hosted, `src/fonts`). Condensed for
  headings, names and scores (`font-display`, `font-score`), Barlow for text and controls.
  Reenie Beanie only for real coach notes, never for invented text. Body 16 px.
- **Colour from the club** (`lib/color.ts`, tested for six club colours in both themes):
  - stage: the raw club colour, text in white or ink by contrast;
  - deep: the club colour mixed with near black (sidebar and phone bars); light club colours
    such as yellow get a neutral `#14171c` instead of an olive;
  - paper: the page tinted 7 % towards the club colour; dark theme tinted near black;
  - accent: the club colour shifted to 4.5:1 for links and buttons;
  - signal: resin yellow `#ffd23f` marks exactly one thing per screen that needs attention
    (a figure below the reference value, the first weakness of the last match); ink for light
    clubs. The current place in the navigation is marked in white, not in the signal colour.
  - green and red only mean goal / no goal, ok / error.
- **Form:** 6 to 8 px radius, no pills, no floating cards; structure from hairlines, paper and
  space. Tables are match sheets (`.sheet`): hairline rows, a firm rule under the head, figures
  right-aligned. No coloured side borders on boxes.
- **Court:** `CourtLines` draws the right goal area of the real court (6 m, dashed 9 m, 7 m mark,
  goal) as decoration (`aria-hidden`); from 1280 px it is a square at the stage's right edge and
  the score stands in its goal area. Lines never run through text; on narrow screens they are
  hidden.
- **Icons:** own SVG icons for navigation and handball objects (`components/shell/icons.tsx`:
  overview court, scoreboard, jersey, cone, scenes, dates, goal, "ask" on the 9 m arc). Lucide
  only for neutral controls (close, search, menu, arrows).
- **Moments:** the score counts up once (about half a second) on the stage; "analysis done" is
  said on the match stage, not in a toast; the match card (4:5 PNG, drawn locally) for sharing.
  All motion respects `prefers-reduced-motion`.

## Voice

The stage states one thing, like someone in the dressing room, and only what follows from the
data (`lib/voice.ts`, tested): a run of results, goals against expected goals, the defence
against expected goals, the record; for a match its margin. Without enough data the title is
neutral. Estimates say so ("geschätzt"); demo data is tagged.

## Components

`components/ui`: `Button` / `buttonClass`, `Card`, `Section`, `Alert`, `EmptyState`, `Skeleton`,
`Badge`, `Segmented`, `Dialog`, `Menu*`, `useConfirm`, `PageHeader`, `BackLink`, form fields.
`components/domain`: `Stage`, `stageButton`, `stageLink`, `StageTag`, `CourtLines`, `MatchScore`
(`useCountUp`), `Jersey`.
`components/shell`: `AppShell`, `TeamSwitcher`, `AccountMenu`, `CommandPalette`, `SubNav`,
`TeamHeader`, `TeamSubNav`, `TrainingHeader`, `NextUp`, `TwoFactorBanner`, icons.

## Writing

- de-CH without ß, fr, en. No long dashes. Short sentences, verbs on buttons ("Spiel anlegen").
- Say what happens next ("Lade das Video hoch. Statistik, Szenen und Erkenntnisse entstehen danach
  automatisch."), not what is missing.

## Accessibility and performance

WCAG 2.2 AA (axe in every Playwright flow), focus ring in the accent colour, skip link, 44 px
touch targets in the tab bar, no horizontal scrolling at 390 px. Budgets: start page under
250 kB first-load JavaScript, other routes under 300 kB, LCP under 2.5 s with 4x CPU throttling.

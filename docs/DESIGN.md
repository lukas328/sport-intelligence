# Design

How the web app looks and behaves, and why. Scope and navigation of the redesign are in ADR
029. The new look is decided in `docs/design/ux-reset/` and still open. The rules below are checked where possible
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

## Navigation (ADR 029)

Scope and structure follow `docs/design/ux-reset/SPEC.md` (sections 1, 6, 7, 9) and ADR 029.
The new look is decided in `docs/design/ux-reset/` and still open; the sections below on
identity and visual language describe what is on screen today.

| Role | Destinations |
|---|---|
| Coach, analyst, team manager, admin | Spiele · Szenen · Saison · Team (start: Spiele) |
| Player, goalkeeper | Start · Team; with Teamfunktionen Start · Szenen · Termine · Team |
| Parent | Start · Team; with Teamfunktionen Start · Termine · Team |
| Guest | Spiele · Team |

- One level of tabs per destination, never two: Szenen → Szenen · Sammlungen · Spielzüge ·
  Tabelle; a match → Spiel · Video · Zahlen; Team → Kader · Termine · Training · Aufgaben only with
  Teamfunktionen. Spiele and Saison have none.
- "Video hochladen" is a button in the sidebar and a + in the phone top bar
  (`matches?upload=1`: pick a played match without video or create one).
- "Teamfunktionen" (team setting, off by default) hides training, dates, RSVP, tasks and the
  player and parent destinations from the navigation and the search; routes stay reachable.
- Account menu: Ich (Profil, Sicherheit, Meine Daten) and Verein (Verein, Teams und Rollen with
  Teamfunktionen, Abo und Rechnungen, Verband), two pages with one tab level each
  (`lib/settings-model.ts`).
- Full screen without the frame: Spieltag (`matches/[m]/matchday`), presentations, remote.
- Old addresses redirect (`/live`, `/marks`, `library`, `search`, `paper`, `settings`, `profile`).

## Key screens

See `SPEC.md`, section 7 for what each screen contains. Built in phase 1 as plain pages:
Szenen (`teams/[t]/scenes`), Sammlungen and a collection (`collections/[id]`, `…/present`), the
shared page for scenes and collections (`/s/[token]`, with Open Graph data), consent by link
(`/einwilligung/[token]`), "Was sich wiederholt" on Saison, "Gegentore nach Position" on the
Spiel tab, the dialog "Spielbericht hinzufügen".

## Identity: "Die Halle" (ADR 024, on screen today; the new look is open)

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

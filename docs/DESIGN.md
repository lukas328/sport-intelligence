# Design

How the web app looks and behaves, and why. Scope and navigation are in ADR 029, the look
«Anlauf» in ADR 030 (source: `docs/design/ux-reset/ANLAUF.md` and `SPEC.md`, which win over this
file where they differ). The rules below are checked where possible
(`apps/web/src/lib/design-lint.test.ts`, `design-types.test.ts`, `nav-model.test.ts`); this file
is the working reference.

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

## Identity: «Anlauf» on «Stoff» (ADR 030)

The result in the club's colour, slanted; the scene on a tactics camera; every line a measured way.

| Zone | Where | Character |
|---|---|---|
| Wurf head | start (Spiele), tab Spiel | club colour, lower edge slanted, slanted title, the result large with two offset outlines, the opponent's goals underlined in its colour, the run of the match as a line |
| Streifen | Video, Zahlen, Prüfen, Spieltag | slim club-coloured band with name and result |
| Seitenkopf with Keil | every page without a match | kick line, slanted title, the Keil: the slanted edge in the club colour |
| Bühne | Video, scene tiles | the tactics camera on a dark court |

One head per screen. Settings and forms get the Seitenkopf.

## Product name and logo

The product is **Handball Intelligence**; the logo is «Taktik» (rules and files in
`docs/design/brand2/taktik/README.md`, files unchanged from `final/`).

- **In the app** only ink: `AppMark` (`components/brand.tsx`, `favicon-32-tinte.svg` below 48 px,
  `zeichen-tinte.svg` above) in front of the club crest, and the browser favicon
  (`app/icon.svg`). The colours in the app belong to the teams.
- **Outside the app** two colours, Markerblau `#1d47d1` and Markerrot `#e1251b`: the word mark
  `wortmarke-quer.svg` on sign-in, onboarding and the website (at least 220 px wide), the app
  icons (web manifest, iOS, Android adaptive and monochrome), the Open Graph image.
- **On a club colour** always one colour (white on blue, red, black, green; ink on yellow, white).
- Technical names stay: `handball-ai.ch` (domain, mail, deep links), `ch.handballai.app`, the
  Expo slug, the Python package `handball_api`, User-Agent strings (Q-PROD-1).

## Visual language

- **Ground:** cloth `#eceae5` with a dot mesh, paper `#f7f6f2` for fields, ink `#16171a`, ink-2
  `#53565b` for secondary text, rule `#d6d3cc`. No dark scheme (open, Q-UX-14).
- **Type:** Kanit italic (titles, numerals, names, navigation, tabs: `font-slant`, `font-num`),
  Hanken Grotesk for everything else (17 px body), IBM Plex Mono only for times on the tactics
  camera. SIL OFL, self-hosted (`src/fonts`). No capitals, no letter-spacing.
- **Colour** (`lib/color.ts` `kit()`, variables via `kitVars()`):
  - club: the area of the three heads, the active marker, our lines (with a piping where the
    colour vanishes on the cloth) and numerals (`--club-text`, 4.5:1); text on it white or ink;
  - opponent: its colour where the opponent is meant (underline of its goals, its lines, the
    chip next to its name); unknown is grey and the screen asks; clash rule by hue;
  - tactics camera: own dots filled, opponents as rings; grey rings only when both teams are of
    the same colour family and similar lightness;
  - yellow `#ffd23c`: «schau hier», always with a word; green and red: win and loss, with the word.
- **Form:** no radius, no shadows; 2 px ink rules under section heads and tabs, 1 px rules between
  rows; tables as match sheets (`.sheet`). Buttons ink: filled for the one action, outlined for
  the others, 48 px.
- **Graphics** (`components/anlauf`): Bundle (goal runs), Zones, Flight, Rail, Series, DiffBars,
  TacticsCamera with BallLine, EmptyField. Only measured data: confirmed solid, estimated dashed,
  no ball flight, no passes; every graphic has a text alternative. Lines draw themselves once;
  `prefers-reduced-motion` shows the end state.

## Voice

The stage states one thing, like someone in the dressing room, and only what follows from the
data (`lib/voice.ts`, tested): a run of results, goals against expected goals, the defence
against expected goals, the record; for a match its margin. Without enough data the title is
neutral. Estimates say so ("geschätzt"); demo data is tagged.

## Components

`components/anlauf`: `WurfHead`, `Strip`, `PageHead`, `Score`, `SectionHead`, `LinkTabs`,
`AttnTag`, `LineKey`, `CameraKey`, `ActiveMark` and the graphics above; `/dev/anlauf` shows them
in the six check colours (development only).
`components/ui`: `Button` / `buttonClass`, `PageHeader` (the Seitenkopf), `Segmented`, `Dialog`,
`Menu*`, `useConfirm`, form fields, `Card`, `EmptyState`, `Skeleton`, `Badge`.
`components/shell`: `AppShell` (top bar, phone top bar and tab bar), `ClubMark` (the crest),
`TeamSwitcher`, `AccountMenu`, `CommandPalette`, `SubNav`, `AreaHeader`, `PageTabs`.

## Writing

- de-CH without ß, fr, en. No long dashes. Short sentences, verbs on buttons ("Spiel anlegen").
- Say what happens next ("Lade das Video hoch. Statistik, Szenen und Erkenntnisse entstehen danach
  automatisch."), not what is missing.

## Accessibility and performance

WCAG 2.2 AA (axe in every Playwright flow), a 3 px ink focus ring, skip link, 44 px
targets, no horizontal scrolling at 390 px. Budgets: start page under
250 kB first-load JavaScript, other routes under 300 kB, LCP under 2.5 s with 4x CPU throttling.

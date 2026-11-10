# Redesign spec: "Halle 2"

Binding reference for the UI rebuild of `apps/web`. The pictures are in `zielbild.html` (open it
in a browser, or rebuild it with `python3 docs/design/ux-reset/build.py`); every screen named
here has a mockup there at desktop and phone width, and its markup in `src/screens/`. The
findings that led here are in `ASSESSMENT.md`.

Where this spec and `docs/DESIGN.md` or ADR 023 / 024 disagree (four other destinations, the
stage, Barlow, the tinted paper), this spec wins. Write ADR 025 for it and update `DESIGN.md` as
part of step 2 below.

UI language is de-CH (no ß, no long dashes), with fr and en. German UI strings below are the
wording to use.

## 1. Scope: the coach, alone

The product is match analysis for the coach: upload a match, get three things, see the scenes
behind them. The test for every feature: **does the coach get something out of it if nobody else
in the club opens the app?**

| Tier | What | Status |
|---|---|---|
| **Core** | upload, three things per match, video with timeline, figures that lead to scenes, the check queue, scene search and collections, season patterns, squad for numbers and names, sharing by link | build now |
| **Next** | drill and play toolkit, training plan, sheet for the hall | keep the code, out of navigation; one line "Dazu üben" per insight stays |
| **Last** | accounts for players and parents: own scenes, "Bist du das?", RSVP, dates, attendance | keep the code, behind a team setting that is off by default |
| **Never** | chat, messages, line-ups, car pools, fees | not built |

Communication stays in the team chat (WhatsApp). The app does not message anyone. It produces
things worth posting there: a collection, the highlights, the three things as an image. One link,
a preview, no account.

The one thing players and parents must do in the core tier is consent, through a link without an
account.

## 2. Principles

1. **Result before machine.** A screen shows what came out. Everything the analysis is unsure
   about goes into one queue ("Prüfen"). A page states once where its numbers come from.
2. **Complete without manual work.** Every screen is useful when the coach has typed nothing.
3. **Picture before text.** Every row that has video behind it shows a mini court (or a still).
   Insights are also drawn: circles on the court, a marked phase on the chart. No sentence under
   a page title explaining the page.
4. **One word per thing** (section 9).
5. **Each material has one job** (section 3).
6. **One primary action per screen**, in ink. Destructive actions are never the primary button.

## 3. Materials

The app is a sheet of paper lying on a hall floor.

| Material | Says | Where | Never |
|---|---|---|---|
| **Boden** (floor) | this is handball | the frame of the app (rail on desktop, top bar and tab bar on phones), the mini court, shot maps, plays, placeholders | as page background behind running text |
| **Papier** | the system speaks | the content sheet, lists, tables, forms, automatic sentences. The **yellow sheet** is reserved for the three things (per match and per season) | cards with border + shadow + tint; yellow for anything else |
| **LED** | score and clock | exactly one board per screen: score in amber, running clock in red | results in lists (those are printed numerals), decoration |
| **Trikot** | the club | crest, stickers, own magnets on the court, own line and last bar in charts, the "Tor wir" key | surfaces, buttons, links, focus rings |
| **Filzstift** (marker) | a person did this | notes at scenes, titles of collections (on tape), confirmed rows (tick), a figure the coach circled | automatic text or state; more than three marks per screen |

The floor carries line fragments of several sports (orange handball arcs, a white, a green and a
navy line), as in any multi-purpose hall. The active destination lies on it as a strip of paper.
Marker strokes are drawn with a seeded jitter (`assets/marker.js`): stable per record, never two
alike. A tick at the end of a row means "confirmed by you"; a row without one is estimated. That
is all the provenance marking there is.

## 4. Tokens

Light theme. `assets/halle.css` has them as CSS variables on `.halle`.

| Token | Value | Use |
|---|---|---|
| `--floor` | `#bcd6dd` | app frame, court |
| `--floor-area` | `#9fc3cd` | goal area, earlier bars in a series |
| `--line` | `#e2560b` | handball lines; the edge between frame and sheet on phones |
| `--line-white` / `--line-green` / `--line-navy` | `#f7fbfc` / `#2f8f5b` / `#27485a` | other sports' lines in the frame only |
| `--paper` | `#fcfcfa` | the sheet |
| `--paper-2` | `#f2f3ef` | chip, recessed cell |
| `--sheet-yellow` | `#ffe57a` | the three things |
| `--ink` | `#14171a` | text, primary button, firm rules |
| `--ink-2` / `--ink-3` | `#4a5359` / `#69737a` | secondary, tertiary text (do not go lighter than ink-3) |
| `--rule` | `#d8dcd6` | hairlines |
| `--harz` | `#ffd23f` | the one signal colour: "Prüfen n", marked phase, largest circle, highlighter |
| `--led` / `--led-red` / `--led-off` | `#ffb21f` / `#ff5a4d` / `#2a2521` | score, clock, unlit segments |
| `--night` / `--night-2` / `--night-rule` | `#101316` / `#1b2024` / `#2b3237` | board, video page |
| `--night-ink` / `--night-ink-2` | `#eef0ed` / `#9aa4a9` | text on night |
| `--win` / `--loss` | `#1b7046` / `#b3261e` | Sieg / Niederlage, ok / error. Nothing else. |
| `--club` / `--club-ink` | per club | raw club colour and the text on it |
| `--club-text` | per club | club colour shifted to 4.5:1 on paper; yellow clubs get a dark ochre, white clubs ink |

Dark theme, "Halle bei Nacht" (designed, not inverted): `--floor #1d3a44`, `--floor-area
#16303a`, `--line #ff7a2f`, `--paper #0e1113`, `--paper-2 #171b1e`, `--sheet-yellow #3a3212` with
`--harz` text for the rank numerals, `--ink #eef0ed`, `--ink-2 #b3bbbf`, `--ink-3 #8a9499`,
`--rule #2a3136`, board `#050607` with a 1 px `--rule` edge, `--win #5ad17e`, `--loss #ff7b6e`.
The video page is night in both themes.

`lib/color.ts` keeps deriving the club values; `--deep`, the club-tinted paper, `--surface-l`,
`--accent-*` and the stage colours go away. Buttons, links and focus rings are ink.

**Radius by role:** sheet, court and yellow sheet 2 px, controls 6 px, board 5 px, sticker 3 px.
No pills. **Shadows:** none, except the 2 px hard edge under a sticker.

### Type

| Role | Face | Setting |
|---|---|---|
| Titles | Bricolage Grotesque (variable: opsz, wdth 75 to 100, wght) | 800, width 80 %, tracking -0.02em, line-height 0.98; 44 px phone, 58 px desktop |
| Heads, buttons, tabs | Bricolage Grotesque | 700, width 86 to 90 %; 15 to 26 px |
| Text | Instrument Sans | 400 body 16 px / 1.45 (the mockups use 15 px to fit the frames), 600 for emphasis, 13 px secondary, 12 px minimum |
| Counted things | Archivo, width 62 %, 900, digits only (subset `0-9 : % + - , . ' ?`) | list results 30 to 44 px, figures 40 to 56 px, tabular |
| Board | DSEG7 Classic Bold (`assets/fonts`, OFL) | 17 / 26 / 46 / 60 px, with the unlit "8" segments behind (`data-ghost`) |
| Hand | Mansalva | 17 px minimum, 21 px default; real notes only |

All are SIL OFL; self-host them in `apps/web/src/fonts` with their licence files and remove
Barlow, Barlow Condensed and Reenie Beanie. Labels are sentence case without letter-spacing. No
all-caps anywhere.

## 5. Components

Existing components in `apps/web/src/components` to reuse, change or drop.

| Component | Looks like | In the code |
|---|---|---|
| **Frame** (`.halle.app`, `.rail`, `.topbar`, `.tabbar`, `.main`) | floor-coloured shell with line fragments; content on a paper sheet (12 px gap, 2 px radius on desktop); on phones floor-coloured top and tab bar with a 3 px orange edge | rebuild `shell/app-shell.tsx` |
| **FormHead** (`.head`) | bold label, 1.5 px ink rule to the edge, optional small text or link at the right | new; replaces `PageHeader` descriptions |
| **YellowSheet** (`.gelb`) | yellow block with a form head and the ranked things | new; replaces `analysis/insights.tsx` presentation |
| **Thing** (`.thing`) | rank numeral, mini court with total length, sentence, sub-line, optional "Dazu üben", "n Szenen" | new |
| **Row** (`.game`, `.led-row`) | margin column with date in numerals, picture, content, result | new |
| **Board** (`.board`, `.board.s`) | night panel, crests, DSEG7 score with ghost segments, time-out lamps | rebuild `domain/scoreboard.tsx`, `domain/match-score.tsx`; drop `domain/stage.tsx`, `domain/court-lines.tsx` |
| **MiniCourt** (`svg.mf`) | half court 20 x 12.4 m, floor colours, own magnets in club colour with white ring, opponents white with ink ring, pass dotted, shot with arrow head | restyle `video/mini-court.tsx`, `analysis/court-half.tsx`, `domain/drill-court.tsx`, `tactics/board.tsx` to one look |
| **Zones** (`svg.zonen`) | counts as circles on the court, area proportional to the count, largest in resin yellow | new |
| **Series** (`svg.reihe`) | one bar per match, last one in club colour; signed variant in win / loss colour | new |
| **GoalGrid** (`.tor`) | 3 x 3 goal with counts, most frequent cell in resin yellow | restyle `analysis/goal-grid.tsx` |
| **Numerals** (`.n`, `.res`) | Archivo condensed black | new |
| **Sticker** (`.sticker`, `.gap`) | white-edged card: club-colour picture with jersey shape, position code, big number; name and one line. `.gap` dashed and empty | new; replaces the roster rows in `roster/` |
| **Mark**, **Tape** (`[data-mark]`, `.tape`) | circle, underline, highlight, tick; off-white strip with torn ends and marker text | new, from `assets/marker.js` |
| **SharePreview** (`.chat`, `.bubble`) | how the link looks in a chat: mini court, title, club, length | new |
| **Button** | ink solid, ink outline, underlined text link. 40 px high, 44 px touch targets. No trailing arrows. | change `ui/button.tsx` |
| **Tabs** (`.tabs`) | text tabs, 2.5 px ink underline; "Prüfen n" as a resin-yellow tab at the right | change `ui/tabs.tsx` |
| **Field, Chips** | 48 px field with 1.5 px ink outline; chips are 3 px rectangles, selected ink | restyle `ui/field.tsx`; drop pill `Badge` |
| **Sheet** (`.sheet`) | match-sheet table: hairlines, firm rule under the head, figures right-aligned, optional tick column | keep |
| **Timeline** (`svg.zeitleiste`) | own goals up in club colour, opponent goals down in white, defence system as a band, marked phase in resin yellow, playhead | new, in the video view |
| **FlowChart** (`svg.flow`) | goal difference over time, one line in club colour, half-time rule, marked phase | new |
| **Icons** | own set, one stroke weight (1.7), never in a circle; active item heavier stroke | extend `shell/icons.tsx` (see `ICONS` in `assets/zielbild.js`); Lucide only for close, chevrons |

Drop as defaults: `ui/card.tsx` (keep only for dialogs), `ui/badge.tsx` pills, page descriptions,
`support/checklist.tsx` and `shell/two-factor-banner.tsx` (both become a dot on the account).

## 6. Navigation

Staff (coach, analyst, team manager, admin): **Spiele · Szenen · Saison · Team**. The start is
Spiele.

- Desktop: rail (212 px) on the floor: crest and team, the ink button "Video hochladen", the four
  destinations (active one as a paper strip with a club-colour dot), at the bottom on a paper
  strip "Suchen" and the account.
- Phone: floor-coloured top bar (crest, team switcher, search, a square **+** = Video hochladen)
  and tab bar with the four destinations.
- One level of tabs inside a destination, never two. A match: Spiel · Video · Zahlen, plus
  "Prüfen n".
- **Ich** (Profil, Passwort, Geräte, Zwei-Faktor, Mitteilungen, meine Daten) and **Verein**
  (Name, Farben, Wappen, Teams, Rollen, Abo und Rechnungen, Verband, Teamfunktionen) replace the
  single settings page; both from the account.
- Full screen without chrome: Prüfen, Spieltag, a collection on the big screen, the shared page.
- With "Teamfunktionen" switched on, players and parents get their existing destinations
  (restyled with the tokens, not redesigned now).

### Routes

| Today | Becomes |
|---|---|
| `/app/[orgId]`, `teams/[t]/matches` | Spiele (start) |
| `matches/[m]` (Video, Analyse, Szenen and nine sub-tabs) | `matches/[m]` with Spiel · Video · Zahlen |
| setup steps, Würfe, Ereignisse, full-screen review | `matches/[m]/check` (Prüfen) |
| `matches/[m]/live`, `…/marks` | `matches/[m]/matchday` (Spieltag) |
| `matches/[m]/scouting`, `opponents/[id]` | "Nächster Gegner" on Spiele and "Gegner" on Saison |
| `…/paper`, match-report link, file import | dialog "Spielbericht hinzufügen" |
| `teams/[t]/library`, `…/search`, `…/matrix`, `…/assistant` | Szenen |
| `…/playlists`, `…/presentations`, `…/assignments` | Sammlung (`collections/[id]`, `…/present`) |
| `/s/[token]` | the shared page |
| `teams/[t]/season` | Saison |
| `teams/[t]`, `…/official`, `…/join-requests`, `…/players/[id]`, settings › Personen | Team |
| `teams/[t]/training`, `drills`, `…/plays` | out of navigation; plays reachable from Szenen and collections, drills from "Dazu üben" |
| `schedule`, `feed`, `consents`, player and parent start | behind "Teamfunktionen"; consent also as a public link |
| `settings`, `profile` | Ich, Verein |
| `/onboarding` (four steps) | two steps |

Old routes redirect. Update `lib/nav-model.ts` and `nav-model.test.ts`; update
`design-lint.test.ts` to the rules in section 12.

## 7. Screens

Mockup and markup: `zielbild.html`, `src/screens/<name>.html`.

### 7.1 Spiele, the start (`spiele.html`)

- **Title** from the state of the last match: "Gewonnen. Und drei Dinge zum Mitnehmen." (or
  "Verloren. …", "Unentschieden. …"), "Gestern war Spiel." (no video), "Die Analyse läuft.",
  "Willkommen." (no match). Line above: opponent and when the analysis finished.
- **Board** of the last match, then the **yellow sheet** with the three things (rank numeral,
  mini court with total length, sentence, sub-line, "n Szenen").
- Actions: "Spiel öffnen" (primary), "Fürs Team zusammenstellen" (creates a collection draft),
  and open check questions as a link with a duration ("3 Fragen offen, 1 Minute").
- **Alle Spiele** as rows: date in the margin, mini court, opponent, one status line, result in
  numerals with "Sieg" / "Niederlage". States: done ("n Szenen"), running (pale court, bar,
  minutes left), no video (dashed slot, link "Video hochladen").
- Side: **Nächster Gegner** (three facts from table and match reports, scenes from the last
  meeting) and the top of the **table**.
- No calendar, no trainings, no RSVP.

### 7.2 Spiel, tab "Spiel" (`spiel.html`)

- **Board** (stays above all three tabs): crests, names, score, half-time, date, hall, time-out
  lamps. Tabs. **Source line**: "Quellen: Video (60 von 60 Minuten) · Spielbericht von
  handball.ch · 21 von 24 Würfen von dir bestätigt"; details behind "Wie gerechnet?".
- **Yellow sheet** with the three things; each may carry "Dazu üben: [drill]".
- Actions: "Fürs Team zusammenstellen", "Highlights teilen", "Als Bild für den Chat" (board and
  three things as an image).
- **Verlauf**: goal difference; a marked phase links to the video at that time.
- **Telegramm**: the newspaper form (result with half-time, hall, goal sequence, penalties, top
  scorers, keeper), generated from the match report; copyable.
- Side: **Gegentore** as zones on the court, **Eigene Würfe** as a shot map (dot = goal, cross =
  no goal), three key figures (the coach can circle one).
- Without video: Telegramm and figures from the match report plus the upload block. Before the
  match: the opponent facts and "Spieltag starten" if no official report is expected.

### 7.3 Spiel, tab "Video" (`video.html`)

- Night page. Small board, tabs, then the video with the match clock as a small red LED.
- **Zeitleiste** below the video; legend in one line.
- Four tools: "Szene merken", "Zeichnen", "Spielerin hervorheben", "Teilen".
- Side: scenes in the visible range (time in numerals, label, running one in resin yellow),
  **Notizen** (handwriting; private until the scene is shared).
- No sub-tabs.

### 7.4 Spiel, tab "Zahlen" (`zahlen.html`)

- Sheets **Feld** and **Tor**; every figure opens its scenes. Last column: a tick when the
  person's assignment is confirmed.
- Side: **Wohin die Gegner trafen** (goal grid), **Phasen** (6 gegen 6, Überzahl, Unterzahl,
  Gegenstösse with partial scores).
- Empty cells stay empty. Running distance appears only once tracks are assigned.

### 7.5 Prüfen (`pruefen.html`)

- Full screen. Head: "Prüfen · Frage 5 von 36", "Später weiter".
- A crop of the frame with the subject boxed in resin yellow; caption with time and why it
  matters.
- The question as the title ("Wer ist das?", "Tor oder kein Tor?", "Ist das der Anwurf?", "Passt
  das Spielfeld?"); answers as large keys, the most likely one first and filled; "Andere",
  "Gegner", "Weiss nicht". Keyboard on desktop.
- Order by value: longest on screen first. Always leavable; each answer is saved at once.

### 7.6 Szenen (`szenen.html`)

- The search field is the page. It takes filters and questions; recognised filters appear as
  chips; the answer is a figure with its base, then the scenes as mini-court tiles, "Alle n
  abspielen", "In eine Sammlung", "Als Tabelle" (the matrix with this selection).
- Empty query: newest scenes and four example searches from the team's own data.
- **Sammlungen** (title on tape, one meta line) and **Highlights** (automatic per match,
  landscape and portrait, people without consent left out).

### 7.7 Sammlung (`sammlung.html`)

- One object replaces playlist, presentation and assignment. Created from the three things with
  one tap, as a draft the coach trims.
- Title on tape. "Link teilen" (primary) and "Am Bildschirm zeigen" (full screen with drawing).
- **Ablauf**: ordered entries of three kinds: scene, play, note (handwriting).
- Side: **So kommt es im Chat an** (the link preview), "Link kopieren", **Geöffnet** (a count,
  validity, "sperren").
- No recipients, no due dates, no per-person read state, no slide editor.

### 7.8 Geteilt (`geteilt.html`)

- The public page behind a shared link, phone first: floor-coloured head with crest and team,
  title on tape, the video, the coach's note at the scene, "Nächste Szene", the list.
- Same page for one scene, a collection and the highlights. No menu, no sign-in, no
  registration prompt. Valid 30 days, unlisted, revocable; people without consent are blurred.
- Open Graph preview: mini court image, title, club, length.

### 7.9 Saison (`saison.html`)

- Title: rank and the most persistent theme ("Rang 2. Und rechts aussen bleibt offen.").
- **Yellow sheet "Was sich wiederholt"**: themes that appear in at least two matches with video,
  each with a sentence, its scenes and a small series (one bar per match).
- **Verlauf** (goal difference per match), **Wer trifft** (sheet), side: **Tabelle**, **Gegner**.
- A figure without data is left out, never shown as a dash, zero or record. Say from how many
  matches a theme comes.

### 7.10 Team (`team.html`)

- The squad from handball.ch as an album by position. Under each sticker one season figure; a
  resin dot marks what is missing (consent, number). A dashed slot is a person without a number.
- Side: **Einwilligungen** (count, one link for the team chat), **Trainerbank** (who can analyse;
  invite an assistant or someone to film or check).
- No availability, no player invitations.

### 7.11 Spieltag (`spieltag.html`)

- Phone, full screen, works offline. Night head with score (amber) and running clock (red).
- Six large keys ("Tor wir" in club colour, "Tor [Gegner]" in ink, "Gute Aktion", "Fehler",
  "Abwehr anschauen", "Später anschauen"), three small ("2 Minuten", "Time-out", "Halbzeit").
- Last entry with "zurücknehmen". "Pro Spielerin erfassen" opens the detailed level. "Link
  teilen" hands the screen to someone on the bench without an account.
- Offered only when no official match report with a goal sequence is expected.

### 7.12 Einstieg (`einstieg.html`)

- Step 1: team search (as today). Step 2 "Das seid ihr, oder?": what handball.ch delivered with
  ticks, the jersey colour as eight jerseys (choice circled), two stickers that take the colour
  at once, "Stimmt, weiter". Then Spiele with one task: first video or demo match.
- Manual squad entry only if nothing was found. Nobody is invited during onboarding.
- Sign-in pages use the same floor, sheet and a board.

### 7.13 States (`zustaende.html`)

Every screen has designed empty, running and error states: say what is going on, show what will
come, offer one action.

- **No video yet**: dashed block with the small board, "Lad das Video hoch. Nach etwa 40 Minuten
  bekommst du die drei Dinge und alle Szenen.", "Video wählen", "Link einfügen".
- **Analysis running**: steps in words with "fertig / läuft / danach", a bar, minutes left, and
  something useful to do meanwhile.
- **Empty list**: one sentence, one or two actions, and the filled layout pale behind it.
- **Error**: what failed, what to do; the loss colour only on the icon.

## 8. Voice

- Titles name the state or one fact from the data. If the data gives no sentence, there is none.
- Figures are concrete with their base ("9 von 18"); percentages only with the base next to them.
- Verbs on buttons; no arrows; "du".
- Say what happens next, not what is missing. Say once where numbers come from.
- No page-explaining sentence under a title. No pills for "Demo", "Neu", "Live".

## 9. Vocabulary

| de-CH | fr | en | Replaces |
|---|---|---|---|
| Spiele | Matchs | Matches | Übersicht, Spielplan |
| Drei Dinge | Trois points | Three things | Erkenntnisse, Was auffällt |
| Szenen, Szene | Scènes, scène | Scenes, scene | Clip, Reel, Markierung |
| Sammlung | Sélection | Collection | Playlist, Präsentation, Folien, Aufgabe |
| Highlights | Temps forts | Highlights | Reel |
| Spielbericht | Feuille de match | Match report | Matchbogen, Matchblatt, Matchbericht |
| Prüfen | Vérifier | Check | setup steps, Würfe prüfen |
| Spieltag | Jour de match | Matchday | Live erfassen, Markieren |
| Suchen | Chercher | Search | Frag deine Daten, Matrix, Szenensuche |
| Teilen, Link teilen | Partager | Share | Mit Spielern teilen, Aufgabe geben |
| Dazu üben | À travailler | Drill for this | |
| Saison | Saison | Season | |
| Team | Équipe | Team | Kader |

Apply in `apps/web/messages/*.json`, the mobile app and e-mails.

## 10. Demo data

`scripts/seed.py` must produce a club that shows the product: three matches with video and three
things each, two more with a match report only, 30 or more scenes per analysed match, shot map
and zones, a confirmed squad with numbers, two season themes, one collection. Plausible, uneven
numbers and regional names. No figure that is a dash, and no zero presented as a best value.

## 11. Accessibility and performance

Unchanged targets: WCAG 2.2 AA, 44 px touch targets, no horizontal scroll at 390 px,
`prefers-reduced-motion`, the JavaScript and LCP budgets in `DESIGN.md`. Specific to this system:

- Ink on the floor colour and on the yellow sheet is above 7:1; secondary text on them is
  `--ink-2`, never `--ink-3`.
- LED text carries the plain value for screen readers (`aria-label="26 zu 18"`); the ghost
  segments are decorative.
- Marker strokes and the frame's line fragments are `aria-hidden`; what a mark means is also in
  text ("bestätigt").
- Handwriting is never below 17 px and never the only place a fact appears.
- Resin yellow and the yellow sheet are backgrounds only; text on them is ink.
- Win and loss always come with the word, never colour alone. Charts have text alternatives.
- Motion: the board switching to a new score and a tick being drawn. Nothing else moves.

## 12. Lint rules to encode

Replace the current design-lint rules with: no `rounded-*` above 6 px; no `shadow-*`; no
`bg-club` on containers or buttons; no `uppercase` with tracking; the yellow sheet only in the
insight components; marker classes only on user-authored data; one `Board` per route; no `→` in
message files; page components without a description prop.

## 13. Order of work

1. **Foundation**: tokens, fonts, components of section 5, a `/dev/halle` page showing all of
   them in both themes and five club colours.
2. **Frame**: four destinations, upload action, search, Ich / Verein, the "Teamfunktionen"
   setting that hides player and team features, ADR 025, `DESIGN.md`.
3. **Match**: Spiele start, board, three tabs, timeline, Prüfen, Spieltag, match-report dialog.
4. **Szenen**: search field, Sammlung, the shared page and its link preview, redirects.
5. **Saison, Team, Einstieg**.
6. **Content**: vocabulary in three languages, demo data, new screenshots in `docs/screens`.

Done when: no screen has two levels of tabs; no screen consists of one sentence; no list with
video behind it lacks a picture; every screen is complete without manual coach input; a shared
link looks in a chat like the mockup; the checks in section 12 pass; the Playwright flows and
axe pass at 390 and 1440 px.

## 14. Assumptions to confirm with Lukas

1. The core is match analysis for the coach; training next, player and parent accounts last,
   communication never.
2. What exists for players and parents is hidden behind a team setting, not deleted.
3. Consent runs through a link without an account.
4. Four destinations: Spiele, Szenen, Saison, Team.
5. "Sammlung" instead of "Besprechung".
6. Mini court as the default preview; stills only with consent. Ink buttons.

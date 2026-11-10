# Redesign spec: "Halle 2"

Binding reference for the UI rebuild of `apps/web`. The pictures are in `zielbild.html` (open it
in a browser, or rebuild it with `python3 docs/design/ux-reset/build.py`); every screen named
here has a mockup there at desktop and phone width, and its markup in `src/screens/`. The
findings that led here are in `ASSESSMENT.md`.

Where this spec and `docs/DESIGN.md` or ADR 023 / 024 disagree (four destinations, the stage,
Barlow, the tinted paper), this spec wins. Write ADR 025 for it and update `DESIGN.md` as part
of step 2 below.

UI language is de-CH (no ß, no long dashes), with fr and en. German UI strings below are the
wording to use.

## 1. Principles

1. **The week, not the archive.** The start screen always has the same three sections: Heute,
   Zuletzt, Kommt. Only the content changes.
2. **Result before machine.** A screen shows what came out. Everything the analysis is unsure
   about goes into one queue ("Prüfen"). A page states once where its numbers come from.
3. **Complete without manual work.** Every screen must be useful when no coach has typed
   anything. Notes, checks and plans are extras.
4. **Picture before text.** Every row that has video behind it shows a mini court (or a still).
   No sentence under a page title explaining the page.
5. **One word per thing** (section 9).
6. **Each material has one job** (section 2). Above all: marker means a person did it.
7. **One primary action per screen**, in ink. Destructive actions are never the primary button.

## 2. Materials

| Material | Says | Where | Never |
|---|---|---|---|
| **Papier** | the system speaks | page, lists, tables, forms, automatic sentences | cards with border + shadow + tint, tinted page |
| **Filzstift** | a person did this | coach notes, titles of Besprechungen (on tape), confirmed answers (tick), declines (strike through the number), figures the coach marked (circle), today's weekday | automatic text or state, more than three marks per screen |
| **LED** | score and clock | exactly one board per screen: match header, last match on Heute, clock in video and Spieltag | results in lists (those are printed numerals), decoration |
| **Trikot** | the club | crest, jersey numerals, own magnets on the court, own line in charts, the dot at the active destination, the "Tor wir" key | surfaces, buttons, links, focus rings |
| **Boden** | this is handball | mini court, shot map, plays, drills, placeholders | outside court drawings (the orange line colour exists only there) |

Marker strokes are drawn with a seeded jitter (`assets/marker.js`): stable per record, never two
alike. Tape (`.tape`) labels things a person named.

## 3. Tokens

Light theme. `assets/halle.css` has them as CSS variables on `.halle`.

| Token | Value | Use |
|---|---|---|
| `--paper` | `#fcfcfa` | page |
| `--paper-2` | `#f2f3ef` | note, chip, recessed |
| `--ink` | `#14171a` | text, primary button, firm rules |
| `--ink-2` | `#4a5359` | secondary text |
| `--ink-3` | `#69737a` | tertiary text (4.5:1 on paper, do not go lighter) |
| `--rule` | `#d8dcd6` | hairlines |
| `--floor` | `#bcd6dd` | court |
| `--floor-area` | `#9fc3cd` | goal area |
| `--line` | `#e2560b` | court lines only |
| `--harz` | `#ffd23f` | the one signal colour: highlighter, "Prüfen n", open count, marked phase |
| `--led` / `--led-off` | `#ffb21f` / `#2a2521` | lit and unlit segments |
| `--night` / `--night-2` / `--night-rule` | `#101316` / `#1b2024` / `#2b3237` | board, video page |
| `--night-ink` / `--night-ink-2` | `#eef0ed` / `#9aa4a9` | text on night |
| `--win` / `--loss` | `#1b7046` / `#b3261e` | Sieg / Niederlage, ok / error. Nothing else. |
| `--club` | per club | raw club colour |
| `--club-ink` | per club | text on `--club` (white or ink by contrast) |
| `--club-text` | per club | club colour shifted to 4.5:1 on paper, for numerals; yellow clubs get a dark ochre, white clubs ink |

Dark theme, "Halle bei Nacht" (designed, not inverted): `--paper #0e1113`, `--paper-2 #171b1e`,
`--ink #eef0ed`, `--ink-2 #b3bbbf`, `--ink-3 #8a9499`, `--rule #2a3136`, `--floor #24414a`,
`--floor-area #1b343c`, `--line #ff7a2f`, `--harz #ffd23f` (text on it stays ink), board
`#050607` with a 1 px `--rule` edge, `--win #5ad17e`, `--loss #ff7b6e`, `--club-text` = club
colour lightened to 4.5:1. The video page is night in both themes.

`lib/color.ts` keeps deriving the club values; `--deep`, `--paper-l` tint, `--surface-l`,
`--accent-*` and the stage colours go away. Buttons, links and focus rings are ink (this is
variant A from `docs/design/identity/FOR_LUKAS.md`, item 8).

**Radius by role:** paper and court 2 px, controls 6 px, board 5 px, sticker 3 px. No pills.
**Shadows:** none, except the 2 px hard edge under a sticker.

### Type

| Role | Face | Setting |
|---|---|---|
| Titles | Bricolage Grotesque (variable: opsz, wdth 75 to 100, wght) | 800, width 80 %, tracking -0.02em, line-height 0.98; 44 px phone, 58 px desktop |
| Heads, buttons, tabs | Bricolage Grotesque | 700, width 86 to 90 %; 15 to 26 px |
| Text | Instrument Sans | 400 body 16 px / 1.45 (the mockups use 15 px to fit the frames), 600 for emphasis, 13 px secondary, 12 px minimum |
| Counted things | Archivo, width 62 %, 900, digits only (subset `0-9 : % + , . '`) | jersey numbers 22 px, list results 30 to 44 px, figures 40 to 56 px, tabular |
| Board | DSEG7 Classic Bold (`assets/fonts`, OFL) | 17 / 26 / 46 / 60 px, with the unlit "8" segments behind (`data-ghost`) |
| Hand | Mansalva | 17 px minimum, 21 px default; real notes only |

All six are SIL OFL; self-host them in `apps/web/src/fonts` with their licence files and remove
Barlow, Barlow Condensed and Reenie Beanie. Labels are sentence case without letter-spacing. No
all-caps anywhere.

## 4. Components

Existing components in `apps/web/src/components` to reuse, change or drop.

| Component | Looks like | In the code |
|---|---|---|
| **FormHead** (`.head`) | bold label, 1.5 px ink rule to the edge, optional small text or link at the right | new; replaces `PageHeader` descriptions and `Section` titles |
| **LedgerRow** (`.led-row`, `.game`) | margin column (weekday, time or date in numerals), content right, hairline below | new; used by Heute, Spiele, Training, Termine |
| **Board** (`.board`, `.board.s`) | night panel, DSEG7 score with ghost segments, team names, time-out lamps | rebuild `domain/scoreboard.tsx`, `domain/match-score.tsx`; drop `domain/stage.tsx`, `StageTag`, `domain/court-lines.tsx` |
| **MiniCourt** (`svg.mf`) | half court 20 x 12.4 m, hall-blue floor, orange lines, own magnets in club colour with white ring, opponents white with ink ring, pass dotted, shot with arrow head | restyle `video/mini-court.tsx`, `analysis/court-half.tsx`, `domain/drill-court.tsx`, `tactics/board.tsx` to one look |
| **Numerals** (`.n`, `.nums`) | Archivo condensed black; `.nums` is the squad as a row of numbers, declines struck through by marker | new |
| **Sticker** (`.sticker`, `.gap`, `.away`) | white-edged card: club-colour picture with jersey shape, position code, big number; name and one status line. `.gap` dashed and empty, `.away` grey | new; replaces the roster rows in `roster/` |
| **Mark** (`[data-mark]`) | circle, underline, highlight, strike, tick | new, from `assets/marker.js` |
| **Tape** (`.tape`) | off-white strip with torn ends, slightly rotated, marker text | new |
| **Note** (`.note`) | paper-2 block with a tape label and handwriting, author and "gesehen von n von m" | new |
| **Button** | ink solid (primary), ink outline, underlined text link. 40 px high, 44 px touch targets. No trailing arrows. | change `ui/button.tsx` |
| **Tabs** (`.tabs`) | text tabs, 2.5 px ink underline; "Prüfen n" as a resin-yellow tab at the right | change `ui/tabs.tsx` |
| **Segmented** (`.seg`) | two halves, ink outline, selected half ink | keep, restyle |
| **Field, Chips** | 48 px field with 1.5 px ink outline; chips are 3 px rectangles on paper-2, selected ink | restyle `ui/field.tsx`; drop pill `Badge` |
| **Sheet** (`.sheet`) | match-sheet table: hairlines, firm rule under the head, figures right-aligned | keep |
| **Timeline** (`svg.zeitleiste`) | own goals up in club colour, opponent goals down in white, defence system as a band, marked phase in resin yellow, playhead | new, in the video view |
| **FlowChart** (`svg.flow`) | goal difference over time, one line in club colour, half-time rule, marked phase | new |
| **Crest** | shield with initials until a logo is uploaded | restyle `shell/club-mark.tsx` |
| **Icons** | own set, one stroke weight (1.7), never in a circle; active item heavier stroke | extend `shell/icons.tsx` (see `ICONS` in `assets/zielbild.js`); Lucide only for close, chevrons |

Drop as defaults: `ui/card.tsx` (keep only for dialogs), `ui/badge.tsx` pills, the page
description under titles, `support/checklist.tsx` and `shell/two-factor-banner.tsx` (both become
entries in Offen).

## 5. Navigation

| Role | Destinations |
|---|---|
| Coach, analyst, team manager, admin | Heute · Spiele · Szenen · Training · Team |
| Player, goalkeeper | Heute · Szenen · Termine · Team |
| Parent | Heute · Termine · Kind |
| Guest | Heute · Spiele · Team |

- Desktop: rail (212 px) on paper with a hairline, crest and team at the top; active item bold
  with a club-colour dot. Below the destinations, fixed: **Offen** (count in resin yellow),
  **Suchen** (the command palette; same engine as the Szenen search), the account.
- Phone: top bar (crest, team switcher, Offen, and for staff a square **+** = Video hochladen),
  tab bar with the destinations.
- One level of tabs inside a destination, never two: Spiele (Spiele · Saison · Gegner), a match
  (Spiel · Video · Zahlen, plus "Prüfen n"), Training (Woche · Baukasten · Anwesenheit).
- **Ich** (Profil, Passwort, Geräte, Zwei-Faktor, Mitteilungen, Einwilligungen, meine Daten) and
  **Verein** (Name, Farben, Wappen, Teams, Rollen, Abo und Rechnungen, Verband) replace the single
  settings page; both from the account menu.
- Full-screen without chrome: Prüfen, Spieltag, Besprechung zeigen.

### Routes

| Today | Becomes |
|---|---|
| `/app/[orgId]` | Heute (per role) |
| `teams/[t]/matches`, `…/season`, `opponents/[id]`, `…/paper` | Spiele with tabs; paper import becomes the "Spielbericht hinzufügen" dialog |
| `matches/[m]` (Video, Analyse, Szenen and nine sub-tabs) | `matches/[m]` with Spiel · Video · Zahlen |
| setup steps, Würfe, Ereignisse, full-screen review | `matches/[m]/check` (Prüfen) |
| `matches/[m]/live`, `…/marks` | `matches/[m]/matchday` (Spieltag), two levels |
| `matches/[m]/scouting` | the pre-match state of `matches/[m]` |
| `teams/[t]/library`, `…/search`, `…/matrix`, `…/assistant`, `feed` | Szenen |
| `…/playlists`, `…/presentations`, `…/assignments` | Besprechung (`briefings/[id]`, `…/present`) |
| `teams/[t]/training`, `drills`, `…/plays` | Training with tabs |
| `teams/[t]`, `…/join-requests`, `…/official`, `…/players/[id]`, settings › Personen | Team |
| `schedule` | Termine for players and parents; for staff the attendance lives on each event |
| `settings`, `profile`, `consents` | Ich, Verein |
| `/onboarding` (four steps) | two steps |

Old routes redirect. Update `lib/nav-model.ts` (five destinations for staff, `scenes` for staff,
no second level in the rail) and `nav-model.test.ts`; update `design-lint.test.ts` to the rules in
section 12.

## 6. Screens

Mockup and markup: `zielbild.html`, `src/screens/<name>.html`.

### 6.1 Heute, coach (`heute.html`)

- **Title** from the moment: "Heute ist Training." / "Heute ist Spiel." / "Gestern war Spiel." /
  "Die Analyse läuft." / "Freie Woche." Date above it.
- **Heute**: today's event as a ledger row. Training: squad as numerals with declines struck,
  "12 von 14 dabei", who is out and why, the plan or a suggestion from the three things.
  Match: opponent, time, who is in, three points on the opponent, "Spieltag starten".
- **Zuletzt** ("Vom Samstag"): small board, the three things (rank numeral, mini court with
  total length, sentence, sub-line, "n Szenen"), "Besprechung bauen", "Spiel öffnen".
  States: no video (upload block, see 6.14), analysis running (steps), fewer than three things
  (show two or one, never filler), no match yet (onboarding task).
- **Kommt**: next two events as ledger rows; for a match rank, last result against them, meeting
  time, "Gegner ansehen".
- **Offen** (side column on desktop, below on phones): up to five entries with an empty box, a
  label and a hint (duration or kind); yesterday's done entries stay one day with a marker tick.
  Sources: Prüfen questions, join requests, sync conflicts, missing consents, two-factor, first
  steps.
- **Fürs Team**: the coach's note for the last match in handwriting, "gesehen von n von m". If
  none: one line "Dem Team einen Satz schreiben".

### 6.2 Spiele (`spiele.html`)

- Title: the table rank ("Rang 2 nach fünf Spielen."), league above. Tabs Spiele · Saison · Gegner.
- One line of record: wins, losses, goals, last five as letters in win/loss colour.
- **Kommt** and **Gespielt** as rows: date in the margin, mini court, opponent, one status line,
  result in numerals with "Sieg" / "Niederlage".
- Four row states: analysis done (mini court of the most notable scene, "n Szenen"), running
  (pale court, bar, minutes left), no video (dashed slot "kein Video", link "Video hochladen"),
  upcoming (empty court, "Vorbereiten").
- **Saison**: table, goal-difference chart per match, key figures with a reference value. A
  figure without data is left out, never shown as a dash or zero, never as a record.
- **Gegner**: per opponent rank, results against them, scenes against them.

### 6.3 Spiel, tab "Spiel" (`spiel.html`)

- **Board** (stays above all three tabs): names, score, half-time, date, hall, time-out lamps.
- Tabs; **source line**: "Quellen: Video (60 von 60 Minuten) · Spielbericht von handball.ch ·
  21 von 24 Würfen von dir bestätigt". This replaces per-figure disclaimers; details behind
  "Wie gerechnet?".
- **Verlauf**: goal difference; a marked phase links to the video at that time.
- **Drei Dinge**, then "Besprechung bauen" and "Highlights teilen".
- **Telegramm**: the newspaper form (result with half-time, hall, goal sequence, penalties, top
  scorers, keeper), generated from the match report; copyable.
- Side: **Wurfbild** (dot = goal, cross = no goal), three key figures (the coach can circle one),
  **Fürs Team**.
- Before the match the same route shows the preparation; without video it shows Telegramm and
  figures from the match report plus the upload block.

### 6.4 Spiel, tab "Video" (`video.html`)

- Night page. Small board, tabs, then video with the match clock as a small LED in the corner.
- **Zeitleiste** below the video (section 4). Legend in one line.
- Four tools: "Szene merken", "Zeichnen", "Spielerin hervorheben", "An jemanden schicken".
- Side: scenes in the visible range (time in numerals, label, running one in resin yellow),
  **Notizen** (handwriting, visible to the team unless switched off).
- No sub-tabs. Defence systems are the band on the timeline; comments, clips, drawings and
  feedback are notes and tools.

### 6.5 Spiel, tab "Zahlen"

No mockup. Sheets only: Team, Spielerinnen und Spieler, Würfe (shot map and goal grid), Torhüter,
Laufleistung (hidden until tracks are assigned). Every figure opens its scenes.

### 6.6 Prüfen (`pruefen.html`)

- Full screen. Head: "Prüfen · Frage 5 von 36", "Später weiter".
- A crop of the frame with the subject boxed in resin yellow; a caption with time and why it
  matters ("60 Sekunden im Bild").
- The question as the title ("Wer ist das?", "Tor oder kein Tor?", "Ist das der Anwurf?", "Passt
  das Spielfeld?"); answers as large keys, the most likely one first and filled; "Andere",
  "Gegner", "Weiss nicht". Keyboard on desktop (number keys, space, U to undo).
- Order by value: longest on screen first. Always leavable; each answer is saved at once.

### 6.7 Szenen (`szenen.html`)

- The search field is the page. It takes filters and questions; recognised filters appear as
  chips; the answer is a figure with its base ("19 von 61 Gegentoren, also 31 %"), then the
  scenes as mini-court tiles, "Alle n abspielen", "In eine Besprechung", "Als Tabelle" (the
  matrix with this selection).
- Empty query: newest scenes and four example searches from the team's own data.
- **Besprechungen** (title on tape, one meta line, "Zeigen" / "Öffnen") and **Highlights**
  (automatic per match, landscape and portrait, players without consent left out).

### 6.8 Besprechung (`besprechung.html`)

- One object replaces playlist, presentation and assignment. Created from the three things with
  one tap, as a draft the coach trims.
- Title on tape. "Zeigen" (primary; full screen with drawing) and "Ans Team schicken" (link for
  the team chat, QR code).
- **Ablauf**: ordered entries of three kinds: scene (mini court, time, label, optional
  handwritten line), play (court), note (handwriting only). Add with "Szene dazu", "Spielzug
  dazu", "Notiz dazu".
- Side: where the draft came from, the link, **Gesehen** as the squad in numerals (grey = not
  yet), "Erinnern".
- No slide editor, no due dates. Remote control, PDF, MP4 and offline are in the menu.

### 6.9 Training (`training.html`)

- Title from the week ("Zwei Trainings bis Rheinau."). Tabs Woche · Baukasten · Anwesenheit.
- **Woche**: ledger of the week including the match. A training shows its plan as blocks
  (minutes in numerals, mini court where the block has one, title, one line), the squad, "Blatt
  für die Halle". An empty one offers "Wie letzten Donnerstag" or the Baukasten.
- Side: Baukasten blocks that fit the three things; tap to add.
- **Baukasten**: drills and plays together as picture tiles; text on open.
- Training times and days off are set once per season in a dialog; sessions follow.

### 6.10 Team (`team.html`)

- Title states the squad ("14 im Kader, einer fehlt noch."), one status line with "erinnern".
- The squad as an album by position. Full sticker = person is in the app; dashed slot = invited
  or asked to join; grey = out today. One status line per person: dabei, verletzt bis …,
  abwesend, Einwilligung fehlt (resin dot).
- Side: **Einladen** (one link and QR for everyone; whoever opens it picks their number),
  **Trainerbank**.
- A person's page: season line, scenes, status, consent, account link. An uploaded photo
  replaces the jersey picture.

### 6.11 Spieltag (`spieltag.html`)

- Phone, full screen, works offline. Night head with score and running clock in LED, period.
- Six large keys ("Tor wir" in club colour, "Tor [Gegner]" in ink, "Gute Aktion", "Fehler",
  "Abwehr anschauen", "Später anschauen"), three small ("2 Minuten", "Time-out", "Halbzeit").
- Last entry with "zurücknehmen". "Pro Spielerin erfassen" opens the detailed level.
- "Link teilen" hands the screen to someone on the bench without an account.

### 6.12 Heute, player (`spielerin.html`)

- Title "Hoi Mia. Heute ist Training."
- **Heute**: event with one switch. Fixed trainings default to "Dabei"; "Abmelden" asks for a
  reason in one tap and optionally until when. Matches and extra events need an answer (both
  halves empty).
- **Vom Samstag**: small board with the player's own line against their own season; their three
  best scenes; "Alle n ansehen".
- **Kommt**: next events; a given answer shows as a marker tick and "dabei".
- Side: **Fürs Team** if written; **Bist du das?** (crop, "Ja, das bin ich", "Nein", how many
  left).
- No ranking against team-mates; no team statistics for youth teams. The match page for players
  is video plus their scenes, without coach tools.

### 6.13 Heute, parent (`eltern.html`) and Einstieg (`einstieg.html`)

- Parent: while consent is open it is the first block: three questions with Ja / Nein and one
  sentence each, then "Speichern" and what happens without the first yes. Then the child's week
  with the same switch. Nothing about the child's video before the first yes.
- Einstieg: step 1 team search (as today). Step 2 "Das seid ihr, oder?": what handball.ch
  delivered with ticks, the jersey colour as eight jerseys (choice circled), two stickers that
  take the colour at once, "Stimmt, weiter". Then Heute with one task: first video or demo match.
  Manual squad entry only if nothing was found. Sign-in pages use the same paper and ink.

### 6.14 States (`zustaende.html`)

Every screen has designed empty, running and error states: say what is going on, show what will
come, offer one action.

- **No video yet**: dashed block with the small board, "Lad das Video hoch. Nach etwa 40 Minuten
  bekommst du die drei Dinge und alle Szenen.", "Video wählen", "Link einfügen", a note on Wi-Fi.
- **Analysis running**: steps in words with "fertig / läuft / danach", a bar, minutes left, and
  something useful to do meanwhile.
- **Empty list**: one sentence, one or two actions, and the filled layout pale behind it.
- **Error**: what failed, what to do, in ink with the loss colour only on the icon.

## 7. Feature decisions

| Feature | Decision |
|---|---|
| Video upload | one action everywhere, resumable, continues in the background |
| Three things | automatic; fewer rather than filler |
| Prüfen | optional queue; new: players confirm their own tracks ("Bist du das?") |
| Team note | new, optional, one per match |
| Note to one player | by-product of sending a scene; no place of its own |
| Assignments with due dates | removed; "gesehen von n von m" instead |
| Besprechung | merges playlists, presentations, assignments; drafted automatically |
| Scene search, matrix, assistant | one search field |
| Live capture and courtside marks | one Spieltag tool, simple level first, helper link |
| Match report import (link, photo, file, sync) | automatic from handball.ch, else one dialog |
| RSVP | fixed trainings are opt-out, per team setting |
| Attendance | from the RSVPs, coach corrects; J+S export later |
| Invite | one link and QR per team |
| Opponent | automatic from table, reports and last meeting |
| Public profile, federation pages, remote control, MP4 export, offline | parked or in menus |
| Line-up, car pools, fees | not built: video first, team management only squad and RSVP |

## 8. Voice

- Titles name the moment or one fact from the data. If the data gives no sentence, there is none.
- Figures are concrete with their base ("9 von 18"); percentages only with the base next to them.
- Verbs on buttons; no arrows; "du"; greeting "Hoi" (de-CH), "Salut" (fr), "Hi" (en).
- Say what happens next, not what is missing. Say once where numbers come from.
- No page-explaining sentence under a title. No pills for "Demo", "Neu", "Live".

## 9. Vocabulary

| de-CH | fr | en | Replaces |
|---|---|---|---|
| Heute | Aujourd'hui | Today | Übersicht |
| Spiele | Matchs | Matches | Spielplan |
| Szenen, Szene | Scènes, scène | Scenes, scene | Clip, Reel, Markierung |
| Highlights | Temps forts | Highlights | Reel |
| Spielbericht | Feuille de match | Match report | Matchbogen, Matchblatt, Matchbericht |
| Besprechung (working title) | Séance vidéo | Briefing | Playlist, Präsentation, Folien, Aufgabe |
| Spieltag | Jour de match | Matchday | Live erfassen, Markieren |
| Prüfen | Vérifier | Check | setup steps, Würfe prüfen |
| Suchen | Chercher | Search | Frag deine Daten, Matrix, Szenensuche |
| Baukasten | Boîte à outils | Toolkit | Übungen, Bibliothek, Vorlagen |
| Offen | À faire | Open | Erste Schritte, Mitteilungen |
| Drei Dinge | Trois points | Three things | Erkenntnisse, Was auffällt |
| Fürs Team | Pour l'équipe | For the team | |
| Dabei / Abmelden | Présent·e / S'excuser | In / Can't make it | Ich komme / Ich komme nicht |
| Bist du das? | C'est toi ? | Is this you? | Spieler zuordnen |
| Blatt für die Halle | Feuille pour la salle | Sheet for the hall | PDF |

Apply in `apps/web/messages/*.json`, the mobile app and e-mails.

## 10. Demo data

`scripts/seed.py` must produce a club that shows the product: one match with video, three
things, 30 or more scenes, a shot map, a confirmed squad with numbers, one Besprechung, one team
note, RSVPs for the week, one player out injured, one open join request. Plausible, uneven
numbers and regional names. No figure that is a dash, and no zero presented as a best value.

## 11. Accessibility and performance

Unchanged targets: WCAG 2.2 AA, 44 px touch targets, no horizontal scroll at 390 px,
`prefers-reduced-motion`, the JavaScript and LCP budgets in `DESIGN.md`. Specific to this system:

- LED text carries the plain value for screen readers (`aria-label="26 zu 18"`); the ghost
  segments are decorative.
- Marker strokes are `aria-hidden`; what they mean is also in text ("abgemeldet", "bestätigt").
- Handwriting is never below 17 px and never the only place a fact appears.
- Resin yellow is a background only; text on it is ink.
- Win and loss always come with the word, never colour alone.
- Motion: the board switching to a new score and a tick being drawn. Nothing else moves.

## 12. Lint rules to encode

Replace the current design-lint rules with: no `rounded-*` above 6 px; no `shadow-*`; no
`bg-club` on containers or buttons; no `uppercase` with tracking; no element with marker classes
fed by non-user data; one `Board` per route; no `→` in message files; page components without a
description prop.

## 13. Order of work

1. **Foundation**: tokens, fonts, components of section 4, a `/dev/halle` page showing all of
   them in both themes and five club colours.
2. **Frame**: navigation, Offen, search, upload action, Heute for all moments, Ich / Verein,
   ADR 025, `DESIGN.md`.
3. **Match**: board, three tabs, timeline, Prüfen, Spieltag, match-report dialog.
4. **Szenen**: search field, Besprechung, redirects.
5. **Training and Team**.
6. **Player, parent, Einstieg**.
7. **Content**: vocabulary in three languages, demo data, new screenshots in `docs/screens`.

Done when: no screen has two levels of tabs; no screen consists of one sentence; no list with
video behind it lacks a picture; every screen is complete without manual coach input; the checks
in section 12 pass; the Playwright flows and axe pass at 390 and 1440 px.

## 14. Assumptions to confirm with Lukas

1. Scope: video first, team management only squad and RSVP.
2. Five destinations for staff.
3. The vocabulary above; "Besprechung" to be tried on two coaches.
4. Mini court as the default preview; stills only with the "Videoanalyse im Team" consent.
5. Ink buttons.

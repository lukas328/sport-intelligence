# Redesign spec

Binding reference for the UI rebuild of `apps/web`. The look is **Anlauf** (decided 12 November
2026), defined in `ANLAUF.md`. The pictures are in `zielbild.html` (open it in a browser, or
rebuild it with `python3 docs/design/ux-reset/build.py`); every screen named here has a mockup
there at desktop and phone width, its markup in `assets/anlauf-screens.js`. The findings that led
here are in `ASSESSMENT.md`.

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
3. **Picture before text.** Every row that has video behind it shows a mini court with the
   measured runs. Insights are also drawn: runs on the court, a marked phase on the timeline. No
   sentence under a page title explaining the page.
4. **Only what is measured.** Positions yes, ball flight and passes no; the ball only at the
   player who holds it, where it was found. Estimated is dashed and says so.
5. **One word per thing** (section 9).
6. **One primary action per screen**, in ink. Destructive actions are never the primary button.

## 3. to 5. Look, tokens, components

Defined in **`ANLAUF.md`**: idea, colour model with club and opponent and the clash rules, zones
(Wurf-Kopf, Streifen, Seitenkopf, Bühne / Taktikkamera, Ball, Spur, Minifeld), meaning colours,
neutrals, type with licences, shapes, motion, the mapping from the earlier building blocks, the
data source of every graphic, the quality bar. Tokens and blocks are in `assets/anlauf.css`, the
colour model in `assets/anlauf-farbe.js`, the graphics in `assets/anlauf-feld.js`.

Components in `apps/web/src/components`, in Anlauf terms:

| Component | Replaces / changes |
|---|---|
| `Frame` (top navigation, tab bar, active marker) | rebuild `shell/app-shell.tsx`; drop the rail |
| `WurfHead`, `Strip`, `PageHead` | rebuild `domain/scoreboard.tsx`, `domain/match-score.tsx`; drop `domain/stage.tsx`, `PageHeader` descriptions |
| `Things` (three things with bundles) | replaces `analysis/insights.tsx` presentation |
| `Bundle`, `MiniCourt`, `Zones` | restyle `video/mini-court.tsx`, `analysis/court-half.tsx`; no pass lines, no arrow heads |
| `TacticsCamera`, `BallLine` | new, in the video view and in an opened thing |
| `Rail`, `Flight`, `Series`, `DiffBars` | new |
| `GoalGrid` | restyle `analysis/goal-grid.tsx`; hand-marked data only |
| `SectionHead`, `Button`, `Tabs`, `Field`, `Chips`, `Sheet` | change `ui/button.tsx`, `ui/tabs.tsx`, `ui/field.tsx`; drop pill `Badge`, `ui/card.tsx` except dialogs |

Drop as defaults: page descriptions, `support/checklist.tsx` and `shell/two-factor-banner.tsx`
(both become a dot on the account).

## 6. Navigation

Staff (coach, analyst, team manager, admin): **Spiele · Szenen · Saison · Team**. The start is
Spiele.

- Desktop: top bar: crest and team, the four destinations (slanted, active one with the club
  marker), at the right "Suchen", the ink button "Video hochladen", the account.
- Phone: top bar (crest, team switcher, search, a square **+** = Video hochladen) and tab bar
  with the four destinations.
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

Mockups: `zielbild.html`, one section per screen (anchor = the id below), desktop and phone.
Markup and wording: the function of the same name in `assets/anlauf-screens.js`. Which head a
screen carries is fixed in `ANLAUF.md` section 3.

### 7.1 Spiele, the start (`#start`, `startDesk`, `startPhone`)

- **Wurf-Kopf** of the last match. **Title** from its state: "Gewonnen. Und drei Dinge zum
  Mitnehmen." (or "Verloren. …", "Unentschieden. …"), "Gestern war Spiel." (no video), "Die
  Analyse läuft.", "Willkommen." (no match). Kick line: opponent and when the analysis finished.
  Result with the opponent's underline, the names, the Verlauf from the goal sequence.
- Actions: "Spiel öffnen" (primary), "Fürs Team zusammenstellen" (creates a collection draft),
  the open check questions as a link with a duration ("3 Fragen offen, 1 Minute").
- **Drei Dinge** in a row: index, numeral, unit, sentence, sub-line, the bundle of runs, "n
  Szenen" with length. Desktop: Punkt 1 switches in the same frame between "Alle 9" (bundle) and
  "Szene 39:55" (tactics camera). Phone: the scene of Punkt 1 as its own section below.
- **Alle Spiele** as rows: date, Minifeld (bundle of that match's Punkt 1; empty with "Analyse
  läuft" or "kein Video"), opponent, one status line, result with "Sieg" / "Niederlage". Running:
  a bar and minutes left. No video: link "Video hochladen".
- Side: **Nächster Gegner** (three facts from table and reports, the bundle of the last meeting,
  its scenes) and the top of the **Tabelle**.
- No calendar, no trainings, no RSVP.

### 7.2 Spiel, tab "Spiel" (`#spiel`)

- **Wurf-Kopf** with both names as the title, date, hall, half time, time-outs, rank. Tabs
  Spiel · Video · Zahlen and "Prüfen n". **Source line**: "Quellen: Video (60 von 60 Minuten) ·
  Spielbericht von handball.ch · 21 von 24 Toren von dir bestätigt"; details behind "Wie
  gerechnet?".
- **Drei Dinge** with bundles; each may carry "Dazu üben: [drill]". Punkt 3 is "Tore vom Kreis"
  (goals from the circle), not "Kreisanspiel": passes are not measured.
- Actions: "Fürs Team zusammenstellen", "Highlights teilen", "Als Bild für den Chat".
- **Punkt 1, geöffnet**: the tactics camera of the selected scene with the Ball-Linie and the
  legend. **Telegramm**: the newspaper form from the report, copyable.
- Side: **Gegentore** and **Eigene Tore** as zones, three figures with their source (Paraden
  marked, Ballverluste from the report, Wurfquote from marked shots).
- Without video: Telegramm and Verlauf from the report plus the upload block (state "Kein
  Video"). Before the match: the opponent facts and "Spieltag starten" if no official report is
  expected.

### 7.3 Spiel, tab "Video" (`#video`)

- **Streifen**, tabs, then the **Bühne**: tactics camera with the switch **Video | Taktik** in
  the same frame (Taktik is the default when the field is confirmed), caption with the scene and
  its thing, Pause, clock.
- **Ball**: a small ball at the player who holds it, only where found; **Ball-Linie** under the
  stage; legend "Ball, nur wo erkannt", "Nummer nur, wo sie gelesen wurde".
- **Rail** below: goals from the report, marked phase, playhead.
- Four tools: "Szene merken", "Zeichnen", "Spielerin hervorheben", "Teilen".
- Side: scenes in the visible range (running one in yellow), **Notizen** (private until shared).
- No sub-tabs.

### 7.4 Spiel, tab "Zahlen" (`#zahlen`)

- Streifen, tabs, one source line. Tables **Feld** (Tore, 7 m, 2 Min from the report; Würfe and
  Quote only from marked shots) and **Tor** (Gegentore from the report, Paraden marked). Every
  figure opens its scenes. Last column: tick when the person's assignment is confirmed.
- Side: **Gegentore nach Position** (zones), **Ziel im Tor** (only hand-marked: "12 von 18
  Toren markiert. Weiter markieren"), **Phasen** with their source.
- Empty cells stay empty. Running distance appears only once tracks are assigned.

### 7.5 Prüfen (`#pruefen`)

- Full screen without navigation: top line "Prüfen · …" and "Später weiter", then the
  **Streifen** of the match.
- A crop of the frame with the subject boxed in yellow; caption with time, seconds in view and
  why ("Nummer nie gelesen").
- The question as the title ("Wer ist das?", "Tor oder kein Tor?", "Ist das der Anwurf?", "Passt
  das Spielfeld?"); answers as large keys with the back number in numerals, the most likely one
  first and filled; "Andere", "Gegner", "Weiss nicht". Keyboard on desktop. Progress as 36
  segments.
- Order by value: longest on screen first. Always leavable; each answer is saved at once.

### 7.6 Szenen (`#szenen`)

- **Seitenkopf** ("152 Szenen aus drei Spielen."), then the search field as the page: filters
  and questions; recognised filters as chips, offered ones dashed; the answer as a numeral with
  its base ("19 von 66 Gegentoren über rechts aussen", "29 Prozent. Gegen Thalwil waren es 9 von
  18."); "Alle 19 abspielen", "In eine Sammlung", "Als Tabelle".
- Scene tiles: the run of that goal on a Minifeld, time, match, what was read ("Nummer 5
  gelesen", "Wurfposition geschätzt"), length.
- Empty query: newest scenes and four example searches from the team's own data.
- Side: **Sammlungen** (slanted title, one meta line) and **Highlights** (automatic per match,
  landscape and portrait, people without consent left out).

### 7.7 Sammlung (`#sammlung`)

- One object replaces playlist, presentation and assignment. Created from the three things with
  one tap, as a draft the coach trims.
- **Seitenkopf** with the title, "Link teilen" (primary) and "Am Bildschirm zeigen".
- **Ablauf**: numbered entries of three kinds: scene (with its run), play (drawn), note (italic
  with the club rule).
- Side: **So kommt es im Chat an** (the link preview card), "Link kopieren", **Geöffnet** (a
  count, validity, "Link sperren").
- No recipients, no due dates, no per-person read state, no slide editor.

### 7.8 Geteilt (`#geteilt`)

- The public page behind a shared link, phone first: the club's name and crest, "von [Trainerin]",
  **Seitenkopf** with the title, the video (Video | Taktik), the coach's note, "Nächste Szene",
  the list with the running scene in yellow.
- Same page for one scene, a collection and the highlights. No menu, no sign-in, no registration
  prompt. Valid 30 days, unlisted, revocable; people without consent are blurred.
- Open Graph preview: the slanted club-colour card with the title.

### 7.9 Saison (`#saison`)

- **Seitenkopf** with rank and the most persistent theme ("Rang 2. Und rechts aussen bleibt
  offen.").
- **Was sich wiederholt**: themes in at least two matches with video, each with a sentence, its
  base, its scenes and a Series (one bar per match, the last in the team's colour).
- **Verlauf** (DiffBars per match), **Wer trifft** (from the reports; no Quote unless shots are
  marked). Side: the bundle of the main theme, **Tabelle**, **Gegner**.
- A figure without data is left out, never shown as a dash, zero or record. Say from how many
  matches a theme comes.

### 7.10 Team (`#team`)

- **Seitenkopf** ("14 im Kader. Bei dreien fehlt noch etwas."). The squad from handball.ch by
  position (Tor, Rückraum, Flügel und Kreis): back number in the club colour, name slanted,
  position, one season figure; what is missing as a yellow word ("Einwilligung fehlt", "Nummer
  fehlt", the number then "?").
- Side: **Einwilligungen** (count, one link for the team chat), **Trainerbank** (who can analyse;
  invite someone to film or check).
- No availability, no player invitations.

### 7.11 Spieltag (`#spieltag`)

- Full screen, works offline. Live **Streifen** with score and running clock.
- Six large keys ("Tor wir" in the club colour, "Tor [Gegner]" in ink with the opponent's colour
  as a band, "Gute Aktion", "Fehler", "Abwehr anschauen", "Später anschauen"), three small ("2
  Minuten", "Time-out", "Halbzeit").
- Last entry with "zurücknehmen". "Pro Spielerin erfassen" opens the detailed level. "Link
  teilen" hands the screen to someone on the bench without an account. Desktop adds the log.
- Offered only when no official match report with a goal sequence is expected.

### 7.12 Einstieg (`#einstieg`)

- Step 1: team search (as today). Step 2 "Das seid ihr, oder?" (Seitenkopf): what handball.ch
  delivered with ticks, the jersey colour as eight shirts, and a preview of the last match's head
  and two squad rows that take the colour at once; "Stimmt, weiter", "Das ist nicht mein Team".
  Then Spiele with one task: first video or demo match.
- Manual squad entry only if nothing was found. Nobody is invited during onboarding.

### 7.13 States (`#zustaende`)

Every screen has designed empty, running and error states: say what is going on, show what will
come, offer one action.

- **Kein Video**: head with result and Verlauf from the report, tab Video greyed, dashed block
  "Lad das Video hoch. Nach etwa 40 Minuten bekommst du die drei Dinge und alle Szenen.", "Video
  wählen", "Link einfügen", the Telegramm.
- **Analyse läuft**: "Die Analyse läuft." in the head with the result from the report, steps with
  "fertig / läuft / danach", a bar, minutes left, something useful meanwhile, three empty fields.
- **Feld nicht bestätigt**: the detected field dashed yellow with four corner handles, "Stimmt das
  Feld?", "Ja, stimmt", "Ecken verschieben". Until then no ways, no positions.
- **Gegnerfarbe unbekannt**: opponent grey with "Farbe offen", the head asks with five shirts,
  grey rings on the camera.
- **Ball nicht erkannt**: the scene plays without a ball; the Ball-Linie reads "Ball in dieser
  Szene nicht erkannt".
- **Leer**: one sentence, one or two actions, the filled layout pale behind.
- **Fehler**: what failed, what is kept, what to do; the loss colour only on the icon.

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
`prefers-reduced-motion`, the JavaScript and LCP budgets in `DESIGN.md`. Specific to Anlauf:

- Text on the club colour and the club colour as text reach 4.5:1 (derived in `lib/color.ts`,
  tested with blue, red, yellow, black, white, green); secondary text is `--ink-2` (6.1:1).
- The result carries the plain value for screen readers (`aria-label="26 zu 18"`); the outline
  echoes are `aria-hidden`.
- Every graphic has a text alternative that says what it shows, including what is estimated and
  where the ball was not found.
- Yellow is a background only; text on it is ink, and it always comes with a word.
- Win and loss always come with the word, never colour alone.
- Motion: the tactics camera (with Pause) and bundles drawing once. With reduced motion both
  show the last frame.

## 12. Lint rules to encode

Replace the current design-lint rules with:

- no `rounded-*` and no `shadow-*`;
- `bg-club` only in `WurfHead`, `Strip`, `PageHead` (the Keil), the active marker, the key "Tor
  wir" and the share card; never on buttons, links, rows or containers of text;
- the italic display face (`font-display italic`) only on headings, numerals, names, navigation
  and tabs; never on `p`, `td`, `input`, `button` labels;
- no `uppercase`, no `tracking-*` above 0;
- `bg-attn` (yellow) only together with a text label;
- no SVG path for a ball flight or a pass: the graphic components take tracks, goals and ball
  stretches only (a type check, not a regex);
- one `WurfHead` or `Strip` per route; no head on `PageHead` routes;
- no `→` in message files; page components without a description prop.

## 13. Order of work

1. **Foundation**: tokens, fonts (self-hosted, OFL), the colour model in `lib/color.ts` with
   tests for six club colours and an unknown opponent, the components of section 3 to 5, a
   `/dev/anlauf` page showing all of them in six club colours.
2. **Frame**: four destinations, upload action, search, Ich / Verein, the "Teamfunktionen"
   setting that hides player and team features, ADR 025, `DESIGN.md`.
3. **Data**: the API fields of `ANLAUF.md` section 10 (goal runs and shot spots, scene tracks,
   ball stretches, field confirmation, opponent colour, themes per match, check queue).
4. **Match**: Spiele start with the Wurf-Kopf, the three things with bundles, tab Spiel, tab
   Video with the tactics camera and the Ball-Linie, tab Zahlen, Prüfen, Spieltag, the
   match-report dialog, all states of 7.13.
5. **Szenen**: search field, scene tiles, Sammlung, the shared page and its link preview,
   redirects.
6. **Saison, Team, Einstieg**.
7. **Content**: vocabulary in three languages, demo data, new screenshots in `docs/screens`.

Done when: no screen has two levels of tabs; no screen consists of one sentence; no list with
video behind it lacks a picture; nothing is drawn that is not measured; every screen is complete
without manual coach input; a shared link looks in a chat like the mockup; the checks in section
12 pass; the Playwright flows and axe pass at 390 and 1440 px in six club colours.

## 14. Assumptions to confirm with Lukas

1. The core is match analysis for the coach; training next, player and parent accounts last,
   communication never.
2. What exists for players and parents is hidden behind a team setting, not deleted.
3. Consent runs through a link without an account.
4. Four destinations: Spiele, Szenen, Saison, Team.
5. "Sammlung" instead of "Besprechung".
6. Mini court with runs as the default preview; stills only with consent. Ink buttons.

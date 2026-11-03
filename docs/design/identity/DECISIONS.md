# Decisions: identity "Die Halle"

Decisions taken without the owner (blueprint section 0). Newest last.

1. **Work on `identity/halle`, pull request to `main`.** The blueprint asks for a branch and a PR;
   earlier work went straight to `main`, but here the owner is away and a PR keeps the change
   reviewable as a whole.
2. **The idea of the blueprint, not the look of the references.** Mid-way the owner wrote that the
   reference screens (`references/halle-*`) are ugly and should not be copied. Kept from the
   blueprint: club colour as a stage at the top of overview, season and match; court lines as the
   motif; a voice that states one thing from real data; own icons; moments (score count-up,
   analysis done, match card); stage versus workbench. Dropped from the references: uppercase
   poster type, 2 px black frames, monospace tables, square-edged everything.
3. **Type: Barlow and Barlow Condensed** (SIL OFL, self-hosted, only the needed cuts) instead of
   Big Shoulders, Barlow and Plex Mono. One family with a condensed display cut reads like a
   scoreboard and a match sheet at once without the poster feel. Reenie Beanie only for real coach
   notes. Archivo is removed. Fonts were taken from the `@fontsource` packages with `npm pack`
   (never added to package.json), so nothing has to be removed again.
4. **Form: 6 to 8 px radius, no pills, no floating cards.** Between the soft panels of before and
   the square references.
5. **Polished, not raw.** The owner added: it must still look like a highly produced app; more love,
   never worse. So the identity comes from care in details (court lines from the real geometry,
   count-up of the score, a form guide of result squares, real coach notes in handwriting, a voice from
   the data) on top of the existing quality, not from a rougher look.
6. **References used** (free, no account): the football Bundesliga's 2021/22 on-air identity draws
   its score graphics from hand-hung stadium scoreboards and lets club colours lead
   (bundesliga.com, "brand refresh: the football takes centre stage"); practitioner lists of AI
   design tells (coloured side border on rounded cards, characterless gradients, dashboard look,
   filler). Several design-tool sites were not reachable from this session.
7. **Signal metric against reference values** (save rate 30 %, shooting 55 %, 12 turnovers per
   match) because there is no league baseline in the data; the page names them as reference values.
8. **Season chart from three matches**; before that a sentence says when it appears. The e2e check
   for the chart changed accordingly (intended change of design).

## Owner feedback after the PR: marker stroke and form guide

The owner found the yellow focus cell (tinted panel with a top bar) and the form chips (panels with
a coloured top line) generic. The focus figure now keeps the plain cell and gets a resin marker
stroke under the number, like a coach marking the match sheet, with the reference value below in
muted text. The form became a classic form guide: one solid square per match with the result
letter, the score and the opponent below. No coloured panel edges remain on the season page.

## Owner request: UX fit test of the navigation, season numbers without boxes

A walk through the coach's main jobs showed that four destinations are enough, but the order and
the contents of Team did not match how a coach thinks. Team mixed people (squad), match statistics
(season) and match material (library); plays sat three levels deep. Now: Übersicht · Spiele ·
Training · Team; Spiele → Spielplan · Saison · Bibliothek, Training → Planung · Übungen ·
Spielzüge · Aufgaben, Team → Kader · Termine. Players, parents and guests keep their navigation
(Team → Kader · Saison). URLs are unchanged, so links and bookmarks keep working.

The owner still found the lower half of the season page generated (rows of boxes). The four
figures became "Die Saison in Zahlen": open rows on the paper, label and reference on the left,
the figure in scoreboard type, a bar on a fixed scale with a tick for the reference (goals against
for goals per match), yellow only for the figure that needs work. Form and bests moved into a side
column; bests and scorers are open lists with hairlines instead of panels.

## Season page with a full season of test data

Reviewed with twelve matches of local test data (not part of the product). Form became a strip of
the last ten matches, newest on the right; the trend became goal difference per match as bars above
and below the line with dates (the last six on phones); scorers show the shirt number in the club
colour, as on the squad page, in two columns on desktop. The onboarding card on the overview became
a slim strip (3/7, next step, button). The fixture list no longer says home or away twice.

## Match, drills and training without panels

- Match stage: the four figures that decide a handball match (shooting, saves, turnovers, xG) as a
  head-to-head table in the stage ink next to the score; below the score on phones. A match with
  events but no video (paper report, demo, marks) opens on its analysis instead of an upload box.
- Analysis, insights, training lists and the calendar tools: open sections under a strong top rule
  (`Sheet` in `components/ui/card.tsx`) instead of panels; strength and weakness as a small
  coloured square with the word instead of a pill.
- Drills: each drill shows a small half court with its area marked (wings, back court, pivot, 7 m,
  goal, or the whole half), drawn from the real court geometry; the list sits on hairlines.
- The calendar import uses the German file picker.

## Second fresh-eyes review (screenshots with a full season)

Ratings 1.5 to 3.5 of 5 before this round. Addressed:
- Training and every empty state: no dashed box; a calm surface with a faint goal area at the edge.
- Overview: the score names both teams; the next match as a fixture announcement (date in scoreboard
  type, opponent, "in 4 Tagen"); the ask box is smaller.
- Season: the stage shows the record (S U N) instead of a last score that argued with the headline;
  columns that are zero in every match are left out; the first column stays put when the table
  scrolls on phones; the "yellow" note only appears when something is marked.
- Match: the main switch (Video, Analyse, Szenen) as underline tabs in display type; zero-only rows
  (7 m, 2 minutes) hidden; one primary action per insight, the others quiet.
- Squad: grouped by position like a match sheet (Tor, Rückraum, Flügel, Kreis); delete only on
  hover on desktop; "Kein Konto" no longer repeated on every row.
- Fixtures: the status only when it asks for something (running, failed, played without video).
Not done: drill-specific players and arrows in the mini courts (would need drawn content per drill),
annotated runs in the match timeline.

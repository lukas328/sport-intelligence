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
   count-up of the score, result edges on the form, real coach notes in handwriting, a voice from
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

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

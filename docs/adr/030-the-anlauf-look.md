# 030. The look: «Anlauf» on the ground «Stoff»

- Status: accepted (built step by step, SPEC.md section 13)
- Date: 2026-11-12
- Supersedes: the identity "Die Halle" of ADR 024 and the visual language of `DESIGN.md` before
  this date; ADR 029 left the look open
- Sources: `docs/design/ux-reset/ANLAUF.md`, `SPEC.md`, `zielbild.html`, `shots/`

## Context

ADR 029 fixed scope and navigation and left the look open. The design round
(`docs/design/ux-reset/`) tried several directions; Lukas chose «Anlauf»: the result in the
club's colour, slanted; the scene on a tactics camera; every line a measured way. The old look
("Die Halle": club-tinted paper, a deep sidebar, a dark theme) made every screen a little club
coloured and nothing in particular stand out.

## Decision

1. **Ground «Stoff».** A neutral cloth `#eceae5` with a fine dot mesh, never tinted by the club.
   Text, buttons and links are ink `#16171a`. One light scheme (a dark one is open, Q-UX-14).
2. **The club colour as an area only in three heads**: the Wurf head (result head of the start
   and the tab Spiel, lower edge slanted), the Streifen (slim head of a match's sub-pages) and the
   Keil (the slanted edge under the Seitenkopf of every other page). Otherwise only in the active
   marker of the navigation (a short slanted band), our own lines and numerals, the crest, the
   key "Tor wir" and the share card. One head per screen.
3. **Two teams, two colours.** The opponent's colour comes from the match or the opponent; unknown
   is grey and the screen asks, nothing is guessed. Clash rule on the cloth by hue (second colour,
   then ink); on the tactics camera grey rings only for the same colour family and a similar
   lightness. `lib/color.ts` `kit()`, tested with blue, red, yellow, black, white, green.
4. **Slanted only titles, numerals, names, navigation and tabs** (Kanit italic 700 to 900);
   text, tables, forms and buttons upright (Hanken Grotesk); times on the tactics camera in IBM
   Plex Mono. All three SIL OFL, self-hosted.
5. **Yellow means «schau hier»** (Prüfen, a marked phase, the running scene), always with a word.
   Green and red only win and loss, always with the word.
6. **Only what is measured is drawn.** A goal is the scorer's run (solid when confirmed, dashed
   when estimated), a shot spot and a thin straight line to the goal; no ball flight, no pass
   lines. The ball appears only as a marker at the player who holds it, where it was found;
   otherwise «Ball in dieser Szene nicht erkannt».
7. **Frame:** one top bar (crest, club, four destinations, Suchen, Video hochladen, account),
   on phones a top bar with search and upload and a tab bar with the four destinations. No
   sidebar. The second level of a destination are slanted tabs under the page head.
8. **Edges, not softness:** no radius, no shadows, 2 px ink rules, 44 px targets.

## Consequences

- `globals.css` holds the tokens; the old token names map onto the neutrals until each screen is
  rebuilt (steps 2 to 7 of SPEC.md section 13).
- The rules of SPEC.md section 12 are tests (`design-lint.test.ts`, `design-types.test.ts`):
  no rounded corners or soft shadows, no capitals or letter-spacing, the club colour as an area
  only in the allowed places (a legacy list that only shrinks), no slanted cells, fields or
  button labels, yellow only with a word, one match head per component, no arrows in UI text,
  graphics typed to take measured data only, page heads without description.
- The theme switch is gone; the `hb_theme` cookie is ignored.
- Ball and holder detection are not part of this work (Lukas: UI first, detection later); the
  ball has its place in the UI and stays hidden while the data is missing (OPEN_QUESTIONS).

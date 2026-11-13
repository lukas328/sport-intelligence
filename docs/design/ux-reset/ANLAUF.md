# Anlauf: the chosen look

Decided on 12 November 2026 (Lukas, after rounds 2 to 5): **Anlauf**, with type variant A
(slanted titles) and the ground «Stoff». This file defines the visual system. It replaces sections
3 to 5 of `SPEC.md` and the earlier candidate `TRIKOT.md`. Everything else in `SPEC.md` stays
binding: scope, navigation, routes, what each screen contains, vocabulary, voice, demo data.

Reference: `zielbild.html` (all screens of `SPEC.md` section 7 at 1280 and 390 px, plus the
states; rebuild with `python3 docs/design/ux-reset/build.py`). Pictures in `shots/`.

| File | Port to |
|---|---|
| `assets/anlauf.css` | tokens into `globals.css`, blocks into components |
| `assets/anlauf-farbe.js` | `lib/color.ts` (kit model, clash rule, contrast) |
| `assets/anlauf-feld.js` | graphic components: Bundle, Zones, Flight, Rail, Series, DiffBars, TacticsCamera, BallLine, Hall |
| `assets/anlauf-screens.js` | reference markup and wording for each page |
| `assets/anlauf-demo.js` | nothing: demo data, but in the shape the API must deliver (section 10) |

## 1. The idea

**The result stands slanted in the club's colour, the scene runs on the tactics camera, and every
line is a measured way.**

The name: the *Anlauf* is the scorer's run before the shot, the one part of a shot the tracking
really measures. It is the motif of the whole app: in the head (the run of the match as goal
difference), in the three things (bundles of runs), on the tactics camera (the same runs moving).

Two tests for every element:
- Is this measured, from the match report, or marked by a person? If not, it is not drawn.
- Is this colour one of the two teams, or «schau hier»? If not, it is ink on cloth.

## 2. Colour model

| Token | Meaning |
|---|---|
| `--club`, `--club-2` | the club's first and second colour (club settings) |
| `--club-ink` | text on `--club`: white or ink, whichever contrasts more (all six demo colours reach 4.5:1) |
| `--club-text` | club colour as text on the ground (numerals, names): shifted towards black until 4.5:1; greys and white fall back to ink |
| `--club-edge` | an ink edge when the club colour vanishes on the ground (white) |
| `--club-line`, `--club-pipe` | own lines in charts; a piping in the second colour or ink when the colour is below 2.4:1 on the ground (yellow, white) |
| `--opp`, `--opp-ink`, `--opp-edge`, `--opp-line`, `--opp-pipe` | the same for the opponent in this match |
| `--club-cam`, `--opp-cam`, `--opp-cam-edge`, `--opp-cam-trail` | the two teams on the dark court of the tactics camera |

- **Opponent colour** comes from the match (jersey colours asked in "Spiel anlegen") or what was
  chosen for this opponent before. **Unknown:** grey `#646b73` (on a black club `#8b9198`),
  «Farbe offen» next to the name, and the head asks «Welche Farbe trägt Thalwil?» with five
  shirts. On the tactics camera the opponents are grey rings. Never guess.
- **Clash rule on the ground:** if the opponent's hue is within 45 degrees of the club's (or both
  are greys of similar lightness), the opponent shows its second colour; if that clashes too, ink.
- **Clash rule on the court:** a colour below 2.2:1 on the court `#0f2333` plays in its second
  colour (a black club shows white dots). If the two teams are then still alike, the opponents
  become grey rings with a light edge; the legend says so. Alike means the same colour family
  (hue within 45 degrees, or two greys) **and** a similar lightness (below 2.5:1): blue against
  navy, red against orange, white against white. Similar lightness alone is no clash: blue
  against red, the most common pairing, keeps both colours (own dots filled, opponents rings).
- Test with the six club colours blue, red, yellow, black, white, green (switch in the Zielbild)
  and an unknown opponent.

## 3. Zones

| Zone | What | Where |
|---|---|---|
| **Wurf-Kopf** | full-width area in `--club`, lower edge cut at a slant (100 % to 80 %). Kick line, slanted title, the result in numerals with two offset outlines behind it, the opponent's goals underlined in `--opp`, names with the opponent's colour chip, and the **Verlauf** (goal difference, ours up) as one line across the bottom | exactly one per screen, only Spiele (start) and tab «Spiel»; also the Analyse-läuft and error states of the start (result from the report) |
| **Streifen** | slim version of the head (124 px desktop, 104 px phone): club name, opponent and date, result with one outline | every sub-page of a match: Video, Zahlen, Prüfen; Spieltag as live strip with the running clock |
| **Seitenkopf** | no area of colour: kick line, slanted title on the ground, underneath only the slanted edge as a **Keil** (wedge, 22 px to 4 px desktop, 14 px phone) in `--club` | pages without a match: Szenen, Sammlung, Saison, Team, Einstieg, the shared page |
| **Bühne / Taktikkamera** | dark court `#0f2333`, positions as dots (own `--club-cam`, opponents `--opp-cam` with edge, referee as grey diamond), ways of the last two seconds, the scorer's whole way, at the end the thin line to the goal and a ring at the shot spot. Below: a bar with Pause, Video/Taktik, clock in Plex Mono | tab «Video», «Punkt 1, geöffnet» in tab «Spiel», Punkt 1 on the start (toggle «Alle 9 / Szene 39:55» on desktop, own section on the phone) |
| **Ball** | a small white ball with a seam, upper right at the dot of the player who holds it, **only while the analysis found the ball in the picture**. No flight, no line between holders. Under the stage the **Ball-Linie**: 6 s with segments «14», «9», «5» in the team colour, gaps hatched «nicht erkannt». If not found at all: «Ball in dieser Szene nicht erkannt» | with every tactics camera |
| **Spur** | the measured lines: Verlauf in the head, Anläufe in the bundles and scene tiles, ways on the camera. Confirmed solid, estimated dashed at 60 % | everywhere a line appears |
| **Minifeld** | half court with the goal at the top, ink lines at 38 %, the runs of one thing as a bundle; one run per scene tile; empty (30 %) with «kein Video» or «Analyse läuft» | game list, scene tiles, Sammlung, next opponent, season theme |
| **Aktive Marke** | a 6 px band in `--club` skewed by 14 degrees under the active navigation item and the active tab | top navigation, tab bar, match tabs |

Never: club colour behind running text, on buttons, links, focus rings or table rows. Buttons and
links are ink.

## 4. Meaning colours

| Colour | Means | Rule |
|---|---|---|
| `#ffd23c` Gelb | «schau hier»: Prüfen n, the marked phase, the running scene, what is missing (Einwilligung fehlt, Nummer fehlt), the field check | background only; text on it is ink; always with a word |
| `#17703f` Sieg / ok | Sieg, «bester Wert», bestätigt (tick) | always with the word or the tick's label |
| `#a8261e` Niederlage / Fehler | Niederlage, the error icon | the word carries it; in errors only the icon is red |

No other colours besides the two teams and the neutrals.

## 5. Neutrals

| Token | Value | Use |
|---|---|---|
| `--ground` | `#eceae5` with a dot mesh (two radial gradients, 6 px, 7 % and 5 % ink) | «Stoff», the page |
| `--paper` | `#f7f6f2` | the search field |
| `--ink` | `#16171a` | text, buttons, firm rules |
| `--ink-2` | `#53565b` (6.1:1 on the ground) | secondary text; nothing lighter for text |
| `--rule` | `#d6d3cc` | hairlines |
| `--court` / `--court-bar` / `--court-text` | `#0f2333` / `#0a0d11` / `#c7ced5` | tactics camera |

There is no dark theme; the tactics camera is the dark element. A dark theme can follow later
with the same model (club colours swap to their second colour where they vanish).

## 6. Type

| Role | Face | Setting |
|---|---|---|
| Titles (page, head, section), names of teams and people, navigation, tab labels | **Kanit** italic 800 | 58 px desktop / 32 to 34 px phone for titles, section heads 26 / 22 px, nav 18 px, tabs 20 / 17 px; line-height .96 |
| Numerals: result, figures, ranks, back numbers, times in lists | **Kanit** italic 900, tabular | result 196 / 100 px, strip 72 / 48 px, things 96 / 64 px, lists 44 / 28 px |
| Text, tables, forms, buttons, the kick line | **Hanken Grotesk** 400 / 600 / 700, upright | body 17 px / 1.45, secondary 15 px, nothing that is read under 14 px (`text-xs` is 14 px in the app) |
| Times and hints on the tactics camera, the index of a thing | **IBM Plex Mono** 500 / 600 | 13 to 20 px, in full ink (no secondary grey) |

Against the betting look: slanted only the four roles above. Sentences, tables, buttons and forms
stand upright. No all-caps, no letter-spacing. Scale: 14 15 17 20 26 34 44 58, numerals 48 to 196.

**For older eyes (UX test, second delivery, H08):** the reader is Hans, 58, reading glasses, large
system text. Content text is never under 14 px, body text 17 px, secondary text 15 px; only mono
labels (camera times, the index of a thing) may be 13 px, and then in full ink. Chart axes 13 px.
Back numbers on the tactics camera at least 14 px (dot 14, 17 on the half court). Every button
carries a word; a symbol alone is not enough. `design-lint.test.ts` refuses smaller sizes.

**Licence and source:** all three are SIL Open Font License 1.1. The Zielbild loads them from
Google Fonts; in the app self-host them in `apps/web/src/fonts` from the `@fontsource/kanit`,
`@fontsource-variable/hanken-grotesk` and `@fontsource/ibm-plex-mono` packages (or the files at
github.com/cadsondemak/Kanit, github.com/marcologous/hanken-grotesk, github.com/IBM/plex), with
the `OFL.txt` of each. Subset Kanit to Latin; only the weights listed. Remove Barlow, Barlow
Condensed, Reenie Beanie.

## 7. Shapes

- **No radius anywhere.** The form of the system is the slant: the head's lower edge, the Keil,
  the active marker (skew 14 degrees), the slanted type.
- **No shadows, no cards.** Structure by section heads (slanted title, 2 px ink rule) and
  hairlines. Areas of colour only for Wurf-Kopf, Streifen, Bühne and the key «Tor wir».
- Buttons: 48 px (44 px small), ink filled or ink outline 2 px, label upright 700. Text links
  underlined, no arrows. Touch targets at least 44 px.
- Spacing 4 8 12 16 24 32 48; page gutter 32 px desktop, 16 px phone; work pages (Zahlen, Prüfen,
  Team) use 48 to 64 px between blocks.
- Icons: only search, plus, tick, drag handle, error; one stroke weight, never in a circle.

## 8. Motion

| What | How | Duration |
|---|---|---|
| Tactics camera | plays the scene (positions sampled from the tracks), holds the last frame, starts again; Pause key | 6 s play, 1.6 s hold |
| Bundles | each confirmed run draws itself once when the thing appears, one after the other; estimated runs fade in | .7 s per run, 140 ms apart, ease `cubic-bezier(.3,.6,.3,1)` |
| Ball | appears and disappears with the stretches where it was found; no tween between players | instant |
| Ball-Linie | a playhead moves with the camera | with the camera |

`prefers-reduced-motion: reduce`: the camera shows the last frame and the key reads «Abspielen»;
all bundles are drawn at once. Nothing else moves: no counting numbers, no hover lifts.

## 9. From earlier building blocks in SPEC.md to Anlauf

| In SPEC.md / earlier | In Anlauf |
|---|---|
| Board (LED scoreboard) | Wurf-Kopf (start, Spiel), Streifen (Video, Zahlen, Prüfen), live Streifen (Spieltag) |
| Yellow sheet with the three things | three things in a row (desktop) or stacked (phone): index, big numeral in `--club-text`, unit, sentence, sub-line, the bundle, «n Szenen» |
| Hall floor frame, paper sheet | cloth ground, top navigation with the active marker on desktop, tab bar on phones |
| FormHead | section head: slanted title, 2 px ink rule, small text or link at the right |
| Mini court with magnets, pass and shot arrow | Minifeld with runs only (no pass, no arrow); one run per scene |
| Zones (circles) | Zones: counts at the zones, estimated shot spots as dots, empty dot = not confirmed |
| Series, FlowChart | Series (one bar per match with video, last one in the team colour); Verlauf as the line in the head; season DiffBars (wins up in club colour, losses as dashed ink outline, label with sign) |
| Timeline | Rail: own goals up in `--club-line`, opponent goals down in `--opp-line`, marked phase yellow, playhead |
| Video page at night | the Bühne; the real video behind «Video» in the same frame |
| GoalGrid from video | «Ziel im Tor»: only marked by hand or from the paper sheet, as «von dir markiert, 12 von 18» |
| Sticker album | squad rows by position: back number in `--club-text`, name slanted, one season figure, yellow word for what is missing |
| Marker tick | green tick with label «bestätigt» |
| Handwritten note, tape title | italic text with a 4 px `--club` rule at the left; collection title slanted |
| LED clock | Kanit numerals (Spieltag), Plex Mono on the camera |
| Share preview | a slanted club-colour card with the title (also the Open Graph image) |
| Kit chip (TRIKOT.md) | colour chip next to the opponent's name and the underline under its goals |

## 10. Data source of every graphic, and what shows when it is missing

| Graphic | Shows | Source (API) | When missing |
|---|---|---|---|
| Result, half time, time-outs | numbers | match report (handball.ch) or a readable scoreboard | «Resultat fehlt» with «Spielbericht hinzufügen»; no head numerals |
| Verlauf in the head | goal difference minute by minute | goal sequence of the report: `report.goals[] = {minute, team}` | head without the line |
| Bundle (three things) | each scorer's run in the 2 to 4 s before the shot, ending at the shot spot, then a thin straight line to the goal | `goals[] = {team, minute, scorer_track, run[[x,y]], shot[x,y], confirmed}`; positions 8 to 10 per second; shot spot estimated as the point nearest the goal in the 10 s before the goal; only goals | empty Minifeld with «kein Video» / «Analyse läuft» |
| Scene tile | the one run of that goal | as above, per goal | empty Minifeld, time and label only |
| Tactics camera | dots, ways, scorer's way, shot ring | `scene.tracks[] = {team: own/opp/keeper/ref, number?, xy[[x,y]]}` in court metres, only with a recognised and confirmed field; number only where read (about a quarter of the time) | without confirmed field: state «Stimmt das Feld?»; without tracks: only the video |
| Ball | the holder, where the ball was found | `scene.ball[] = {from, to, track_id}` (stretches where the ball was found in the picture and assigned to a player) | no ball marker; Ball-Linie reads «Ball in dieser Szene nicht erkannt» |
| Zones | count per zone, shot spots | estimated shot spots of the goals → zone | «noch nicht bestätigt» (empty dots); no zone figure without video |
| Ziel im Tor (3x3) | corners | only marked by hand or from the paper sheet | «Noch nicht markiert. Markieren» |
| Tables Feld / Tor | goals, 7 m, 2 min; shots, saves | report; shots and saves only marked by the coach; tick = person assignment confirmed | empty cells stay empty; no dashes, no zeros |
| Phasen | Über-/Unterzahl, Gegenstösse | power play from the 2-minute penalties of the report; fast breaks estimated from the video (`phases[] = {kind, from, to, goals_us, goals_them, estimated}`) | only the report-based rows |
| Rail | goals of both teams, marked phase | goal sequence of the report; phase from the thing | without report: only the playhead |
| Ballverluste | times | only from the report, no position | figure without scenes |
| Season themes, Series | a pattern in at least two matches with video | per match counts of the theme (`themes[] = {key, per_match[{match, count, of}]}`) | theme left out, with «aus n Spielen mit Video» |
| DiffBars, Wer trifft, Tabelle | goals per match, scorers, table | reports and the league table | rows of matches without a report left out |
| Prüfen crop | one person, boxed | `checks[] = {kind, frame_ref, box, seconds_in_view, candidates[]}` | the check is not asked |
| Share preview | title, club, length | collection | title only |

## 11. Quality bar

- **Calm where people work.** Zahlen, Prüfen and Team carry no colour area besides the Streifen
  or the Keil. If a screen feels noisy, remove colour, not content.
- **Right with every club.** Text on the club colour at least 4.5:1, club colour as text at least
  4.5:1 on the ground (checked for blue, red, yellow, black, white, green: 5.0 to 18:1 and 4.6 to
  15:1). Lines below 2.4:1 get a piping. Measured in `shots/farben.jpg`.
- **Honest.** Nothing drawn that the analysis does not measure. Estimated is dashed and says so.
  Missing data is a sentence, never a dash or a zero.
- **Precise.** No overflow at 390 px, no overlapping or clipped text, no single orphan words in
  titles (`text-wrap: balance`), tabular numerals in tables.
- **Not a template.** The list «Was wir nicht tun» in `zielbild.html` applies, including the
  betting look: no neon, no odds tiles, no black-and-yellow as app colours, no slanted body text.
- **Accessible.** WCAG 2.2 AA, 44 px targets, every graphic with a text alternative, colour never
  the only signal, `prefers-reduced-motion`.

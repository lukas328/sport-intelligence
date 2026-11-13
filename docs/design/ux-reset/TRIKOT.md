> **Verworfen am 12. November 2026.** Ersetzt durch `ANLAUF.md`. Nur noch zum Nachlesen.

# Trikot: the chosen look

Decided on 10 November 2026: the app wears the kit. This file defines the visual system. It
replaces sections 3 to 5 of `SPEC.md` (materials, tokens, components), which still describe the
earlier direction "Halle". Everything else in `SPEC.md` stays binding: scope, navigation, routes,
what each screen contains, vocabulary, voice, demo data, order of work.

Reference mockup: direction 2 in `richtungen.html` (`richtungen/2-trikot.html`, styles under
`.tri` in `richtungen/richtungen.css`). It shows the start screen only and is a first sketch, not
the final quality bar.

## 1. The idea

**Every match is two kits.** Colour belongs to the teams, never to the app. The app itself is
neutral cloth and ink. A club opens it and sees its own colours; a match shows the meeting of two
colours; an insight is the back of a shirt with a number.

The test for any use of colour: is this one of the two teams, or one of the referee's cards? If
neither, it is ink on cloth.

## 2. Kit model

| Token | Meaning |
|---|---|
| `--kit-a`, `--kit-b` | club's first and second kit colour |
| `--kit-pattern` | `uni`, `stripes` (vertical), `hoops` (horizontal), `sash` (diagonal band), `halves` |
| `--kit-ink` | text on `--kit-a` (white or ink by contrast) |
| `--kit-text` | `--kit-a` shifted to 4.5:1 on cloth, for numerals and names; white and yellow kits fall back to ink with a kit-coloured hard shadow |
| `--opp-a`, `--opp-ink` | the opponent's colour in this match and the text on it |

- The club picks two colours and a pattern at onboarding and sees the shirt change at once.
- The opponent's colour comes from the match's jersey colours (the app already asks for them in
  "Spiel anlegen") or from what was chosen for that opponent before. Unknown: neutral
  `#3d4449`, and one tap on the kit chip asks "Welche Farbe trägt Thalwil?" (eight shirts).
  Never guess a colour.
- **Clash rule**, as with real away kits: if `--opp-a` is too close to `--kit-a` (same hue
  family and similar lightness), the opponent is shown in its second colour, or in ink.
- `lib/color.ts` keeps deriving the contrast values; test it with red, blue, green, yellow,
  black, white and orange kits in both themes.

## 3. Where colour goes

| Zone | What | Rule |
|---|---|---|
| **Brust** (chest) | the match head: split diagonally into home and away colour, kit pattern on the home side, goals as flock numerals | exactly one per screen, only on screens about one match (start, match tabs, shared page, matchday). Compact (about 120 px) on Video and Zahlen. |
| **Bund** (waistband) | a 10 px band in the kit pattern at the top of pages without a Brust | Szenen, Saison, Team, settings |
| **Rückennummer** | ranked insights, players, answer keys in Prüfen | numeral in `--kit-text` with a 3 px hard shadow; name above in flock |
| **Kit-Chip** | two-tone square for a match in lists: home colour and opponent colour, hard diagonal | the picture of a match without video; with video the mini court sits next to it |
| **Magnete, Linien** | own players and own series in `--kit-a`, opponent in `--opp-a` | court, timeline, charts |
| **Binde** (captain's armband) | the active navigation item and the active tab | `--kit-a` with two thin stripes in `--kit-ink` |

Never: kit colour behind running text longer than two lines, on buttons, links, focus rings or
table rows. Buttons are ink.

## 4. The referee's cards: meaning

| Colour | Card | Means |
|---|---|---|
| `#ffd23f` yellow | Verwarnung | needs attention: "Prüfen n", a marked phase, something missing |
| `#c62828` red | Disqualifikation | loss, error |
| `#1b7046` green | Team-Time-out | win, done, confirmed |

Shown as a small card shape (upright rectangle, 2 px radius) or as a patch. Always with the word,
never colour alone. These three are the only colours besides the kits and the neutrals.

## 5. Neutrals, type, shape

| Token | Light | Dark ("Flutlicht") |
|---|---|---|
| `--cloth` (page) | `#f6f5f2` | `#121416` |
| `--piece` (objects) | `#ffffff` | `#1b1e21` |
| `--ink` | `#14171a` | `#f1f0ec` |
| `--ink-2` / `--ink-3` | `#555d63` / `#6b737a` | `#b4bbc0` / `#8b9399` |
| `--rule` | `#d9d8d3` | `#2c3136` |
| `--seam` (stitching) | `rgb(20 23 26 / 0.38)` | `rgb(241 240 236 / 0.4)` |

- **Flock**: Big Shoulders (variable, opsz 10 to 72, wght 700 to 900), upper case, slight
  positive tracking on small sizes, line-height 0.95. Only for: the page title, section heads,
  navigation, button labels, names and numerals. Big numerals get a hard offset shadow
  (3 to 4 px, no blur).
- **Text**: Sofia Sans 400 / 600 / 700, body 16 px / 1.45, tabular figures in tables. Sentences
  are never upper case.
- No handwriting, no LED, no paper metaphors. A coach's note is italic text behind a small
  captain's "C" badge.
- **Radius**: 0 on cloth pieces and kit zones, 2 px on cards (the referee's), 4 px on inputs.
  **Shadows**: only hard offsets on flock numerals and under buttons (2 px, no blur).
- Fonts are SIL OFL; self-host them in `apps/web/src/fonts`.

## 6. Details that carry the idea

Use each where it means something; none of them is decoration to sprinkle.

| Detail | Looks like | Stands for |
|---|---|---|
| **Naht** (seam) | 2 px dashed line in `--seam` | the edge of a cloth piece: frames insight backs, underlines section heads |
| **Kragen** (collar) | a half-round notch at the top centre of a back, edged in `--kit-a` | this piece is a shirt back: insight or player |
| **Aufnäher** (patch) | small label with a stitched edge | a state: "Analyse läuft", "kein Video", "Nummer fehlt" |
| **Pflegeetikett** (care label) | narrow white tag, small type, sewn at one edge | where the numbers come from: "Video 60 von 60 Minuten · Spielbericht · 21 von 24 bestätigt" |
| **Mesh** | faint dot texture | only on the Brust |
| **Leeres Trikot** | shirt outline in `--seam`, dashed | nothing here yet: no video, no number, empty list |

## 7. From the earlier components to these

`SPEC.md` section 7 names components of the earlier direction. Read them as follows.

| In SPEC.md | In Trikot |
|---|---|
| Board (LED scoreboard) | Brust |
| Yellow sheet with the three things | three Rückennummern (stacked on phones, a row on desktop) |
| Frame of hall floor, paper sheet | cloth page; top navigation on desktop with the Binde on the active item; tab bar on phones |
| FormHead | flock section head with a seam underneath |
| Mini court | same geometry; white floor, goal area tinted 16 % towards `--kit-a`, ink lines, own magnets `--kit-a`, opponents `--opp-a` |
| Zones, Series, FlowChart, Timeline | same charts; own values `--kit-a`, opponent `--opp-a`, marked phase yellow |
| Sticker album | squad as shirt backs: name arched above the number, position as a patch |
| Marker tick ("confirmed by you") | green card with a check |
| Marker circle, underline, highlight | not used |
| Tape title of a collection | flock title |
| Handwritten note | italic text with the "C" badge |
| LED clock (video, matchday) | flock numerals in ink |
| Resin-yellow signal | yellow card |
| Row with margin date | row with kit chip, opponent in flock, date in text, result in flock |
| Share preview | a card split in both colours with the title in flock; this is also the Open Graph image |

## 8. Quality bar

The start mockup is loud and a little raw. The finished system must be:

- **Calm where people work.** Tables, the video view and Prüfen are neutral; the kits appear as
  numerals, magnets and one Brust. If a screen feels noisy, remove colour, not content.
- **Right with every kit.** Check each screen with at least: red/white stripes, blue/yellow
  hoops, yellow/black, white/black, black/red, green uni. Yellow and white must stay legible.
- **Precise.** One spacing scale (4 px steps), one type scale, optical alignment of flock
  numerals, no clipped or overlapping text at 390 px, no orphaned single words in titles.
- **Not a template.** No rounded cards with soft shadows, no pills, no gradient washes, no icon
  in a coloured circle, no trailing arrows, no "Demo" badges. The list "Was wir nicht tun" in
  `zielbild.html` applies.
- **Accessible.** WCAG 2.2 AA, 44 px touch targets, `prefers-reduced-motion`, colour never the
  only signal.

# UI/UX backlog after the app-wide audit

Source: a fresh-eyes audit of every page outside the match page (screenshots light and dark,
desktop and phone, local stack with test data), against `REFERENCES.md` and the rule set in
`REPORT.md`. P1 = broken or misleading, P2 = clearly generated or unclear, P3 = polish.
Worked through in batches; each batch is one or a few commits. `[x]` = done.

## Batch 1: across all pages (fix once, shows everywhere)

- [x] P1 Server-render error after sign-in (AppShell without translations, a 500 on the first page
  after login): the login form does a full load instead of push plus refresh.
- [x] P1 Second-level navigation on phones is a filled black pill -> underline tabs.
- [x] P1 The page title names the section, not the page (Übungen, Spielzüge, Aufgaben say
  "Training"; Bibliothek, Playlists, Präsentationen, Matrix, Assistent, Suche say "Spiele"; Kader,
  Termine say "Herren 1") -> H1 = the page, section as eyebrow or back link.
- [x] P2 Empty states: a tinted panel with display type and a clipped goal arc, most without a next
  step -> calm sentence in body type with one action.
- [x] P1 Native file inputs in English ("Choose File / No file chosen") on Papier, the club logo,
  the calendar import -> one German file button.
- [x] P1 Wording: raw key "search.type_timeout"; "1 Siege"; averages as "18.0"; "z.B."; "Smart
  Playlist"; "Free", "Fair Use".
- [x] P2 Phone tab bar: the indicator is already flush at the top edge of the active tab; the
  floating strip was an artifact of full-page captures.
- [x] Decision for the owner (options A, B, C written in `docs/design/identity/FOR_LUKAS.md`, item 8): club red is the accent, so for a red club primary buttons and links
  read like errors (red means goals against and errors). Options in `FOR_LUKAS.md`.

## Batch 2: courtside tools (used under pressure)

- [x] P1 Live: own "Tor" is the red button -> ink; "Gegentor" carries red. Action buttons below
  the fold on phones -> sticky action bar. Team names instead of "Wir / Gegner"; "1. HZ 0:00".
- [x] P1 Markieren (undo needs an API to delete a mark: for the analysis session): six buttons in six colours -> neutral outlines, red only for the opponent's
  goal; no feedback after a tap -> status line with the last mark and undo; match context.

## Batch 3: team and training

- [x] P1 Kader (numbers stay in the club colour: identity decision, see the red-club note): a trash icon on every row on phones -> in a "…" menu; position codes as pills,
  shirt numbers in red -> plain small caps, ink numbers.
- [x] P1 Termine (the calendar import stays under Training, folded): staff see the player copy and no action -> staff copy, "Training anlegen",
  calendar import moved here from Training.
- [x] P1 Aufgaben (the date field follows the browser language; the US format came from the en-US test browser): date field in US format; "Art" defaults to an empty playlist list with a
  disabled button and no reason -> de-CH date, the first kind with content, a reason line.
- [x] P1 Übungen: twelve filter pills push the list below the fold on phones -> one scrolling row of
  underline links. "Neue Übung" needs an API (the drills are a fixed library): moved to Later.
- [x] P1 Spielzüge (search stays for staff: it searches the templates; the court colour is the identity's court token): search and filters shown with zero plays; templates in dashed tiles; green court.
- [x] P2 Training: "Kalender abonnieren" and ICS import fill the planning page; empty state without
  action.

## Batch 4: library and tools

- [x] P1 Suche: rows without match clock, own and opponent identical, half without video and
  without a reason, 135 rows in a card -> match clock, team, "ohne Video", hairline rows, paging.
- [x] P1 Matrix: "Jede Zelle führt zu den Szenen" but cells are plain text; rows "#6" without
  names; "Wir"; two red primaries for CSV and Excel; filters in a card fill the phone screen.
- [x] P1 Assistent: on phones the input is below the fold; pill input; suggestion cards.
- [x] P2 Bibliothek: the "Szenensuche" black banner; "0" counts with "Alle anzeigen" into empty
  lists; "Smart Playlist".
- [x] P2 Playlists, Präsentationen: two different create patterns, card around one field, boxed
  back icon.
- [x] P1 Papier: "Auslesen" active before a photo; no title or back link; card around one field.

## Batch 5: account, opponent, scouting

- [x] P1 Einstellungen: ~150 device sessions make the page 11 500 px long; a full red bar for
  "Teams 2 / 1" while limits are off; plan cards inside the plan card.
- [x] P1 Profil, Einwilligungen (the squad says whose consent is missing; a full consent table stays in Later): a coach gets an empty state about "deinen Kindern"; no team
  consent overview before filming.
- [x] P1 Gegner: shooter numbers with names from the opponent's squad, open columns, the squad editor after the figures.
  Home or away per game needs the profile API to return it (Later).
- [x] P1 Scouting: no opponent or date in the title; the empty state contradicts its button.

## Review round 1 over batches 4 and 5

A fresh-eyes review scored the new pages; weakest were Gegner (whose result, zone counts) and
Einstellungen (still cards, a full bar for "Teams 2 / 1"). Fixed after the review:

- [x] Gegner: "Unsere Bilanz gegen sie", Sieg/Niederlage and "unser Resultat zuerst" on game rows,
  "13 von 18 Toren mit Zielpunkt erfasst".
- [x] Einstellungen: no cards (section rules), usage as plain text while limits are off, plan price
  "CHF 0 pro Monat" instead of "Gratis gratis", a gap under "Alle … Geräte anzeigen".
- [x] Disabled primary buttons in neutral grey everywhere (a faded club red read like an error).
- [x] Szenensuche: own shirt numbers with names, labelled filter groups that scroll on phones,
  "Eigener Clip" instead of a bare "Clip", "Ansehen" with a play mark and no underline wall.
- [x] Assistent: "Noch keine Gespräche."; Matrix: "Letzte Spiele" shows "alle".
- [ ] Kader (phone): "Kader" three times (H1, tab, group heading); "Liste bearbeiten" alone; the
  red "Spieler hinzufügen" competes with the red numbers (depends on the club-red decision).
- [ ] Sidebar highlight for tools (Assistent, Suche, Gegner) should follow the back link.
- [ ] Einstellungen on phones: the section tabs have no active underline and are cut at the edge.
- [ ] Gegner: back link "Zurück" without eyebrow; the zone "Fernwurf / leeres Tor" mixes two
  situations (analysis data, already reported).
- [ ] Dates: "29. Okt. 26" (Suche) and "29.10.2026" (Gegner): one format.

## Later (features)

- Opponent profile: home or away per game (API field).
- Own drills ("Neue Übung"): needs a drills API; the library is static today.
- Player status (verletzt, abwesend) on the squad; attendance on units and dates; assignment
  progress ("8 von 14 erledigt"); recurring training slots; a team consent table for staff.

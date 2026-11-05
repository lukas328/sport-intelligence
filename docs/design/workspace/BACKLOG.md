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
- [ ] Decision for the owner: club red is the accent, so for a red club primary buttons and links
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
- [ ] P1 Übungen: no "Neue Übung"; twelve filter pills push the list below the fold on phones.
- [x] P1 Spielzüge (search stays for staff: it searches the templates; the court colour is the identity's court token): search and filters shown with zero plays; templates in dashed tiles; green court.
- [x] P2 Training: "Kalender abonnieren" and ICS import fill the planning page; empty state without
  action.

## Batch 4: library and tools

- [ ] P1 Suche: rows without match clock, own and opponent identical, half without video and
  without a reason, 135 rows in a card -> match clock, team, "ohne Video", hairline rows, paging.
- [ ] P1 Matrix: "Jede Zelle führt zu den Szenen" but cells are plain text; rows "#6" without
  names; "Wir"; two red primaries for CSV and Excel; filters in a card fill the phone screen.
- [ ] P1 Assistent: on phones the input is below the fold; pill input; suggestion cards.
- [ ] P2 Bibliothek: the "Szenensuche" black banner; "0" counts with "Alle anzeigen" into empty
  lists; "Smart Playlist".
- [ ] P2 Playlists, Präsentationen: two different create patterns, card around one field, boxed
  back icon.
- [ ] P1 Papier: "Auslesen" active before a photo; no title or back link; card around one field.

## Batch 5: account, opponent, scouting

- [ ] P1 Einstellungen: ~150 device sessions make the page 11 500 px long; a full red bar for
  "Teams 2 / 1" while limits are off; plan cards inside the plan card.
- [ ] P1 Profil, Einwilligungen: a coach gets an empty state about "deinen Kindern"; no team
  consent overview before filming.
- [ ] P1 Gegner: (figures as one open row with "pro Spiel" done) KPI tiles, dead shooter numbers, games without who is home.
- [ ] P1 Scouting: no opponent or date in the title; the empty state contradicts its button.

## Later (features)

- Player status (verletzt, abwesend) on the squad; attendance on units and dates; assignment
  progress ("8 von 14 erledigt"); recurring training slots; a team consent table for staff.

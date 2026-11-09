# UI/UX backlog after the app-wide audit

## Work queue of the UI session (2026-11-09, worked top to bottom)

One ordered list from this backlog, `PROGRESS.md` ("Open"), the handover and the review rounds.
Bugs reported from the test environment on Azure always go first. `[x]` = done.

**A. Now (UI only, the API is there)**
1. [x] Matrix: season choice ("Saison": this and last, one season, all; e2e in `data.spec.ts`). The API reads `season_ids` (top level of the request, default the
   current and the previous season) since 95132d3; the note further down is outdated.
2. [x] Würfe: full-screen review like the goal candidates (the clip plays itself, one key per
   decision); priority 3 of the handover (one-click confirmation on real footage).
3. [x] Gegner: the back link leads to the fixtures and the header follows the other pages
   (eyebrow, title); the zone split stays with the analysis session.
4. [x] Timeline: a label per side on the sided lanes (own team above, opponent below), not only
   in the legend.
5. [x] Check and close (both fine at 390 px and in the search; closed): "Teilen" and "…" on phones (they share the row with the tabs since the
   identity rework); search hits without a video window ("ohne Video" handles them).
6. [x] Analyse tab slice (review round and fixes in PROGRESS.md): possession, attacks, physical load and shots in the language of the
   match sheet, then a fresh-eyes review round (METHOD.md).
7. [x] Attendance (on the match page for staff: replies and who came; the squad keeps its status for B): the API has it (`/attendance/{kind}/{id}`, `/me/attendance`); the training
   view records it. Show who comes on the squad and the dates for staff.

**B. Needs the backend first (to raise with the main session)**
- Player status (verletzt, abwesend) on the squad.
- Assignment progress ("8 von 14 erledigt") for staff.
- Recurring training slots.
- A team consent table for staff (who consented to what, before filming).
- Own drills ("Neue Übung"): a drills API; the library is static today.
- A player's personal season line linked to the clips (per-player figures over the season).

**C. Waiting for others**
- Bugs from the test on Azure (local session sets the environment up, Lukas tests).
- Analysis data reported in `PROGRESS.md` ("Backend findings", "Open"): goalkeeper insight, xG
  against goals, the zone "Fernwurf / leeres Tor", implausible sprint figures, the matching
  window of goal candidates.

**D. Kept by decision**
- Event keys stay English mnemonics (G, S, M, P, T) until a coach asks; German letters collide.

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
- [x] Kader (phone): "Kader" three times (H1, tab, group heading); "Liste bearbeiten" alone; the
  red "Spieler hinzufügen" competes with the red numbers (the button colour waits for the club-red
  decision; heading and edit button fixed).
- [x] Sidebar highlight for tools (Assistent, Suche, Gegner) follows the section; the official data and join requests keep Team · Kader.
- [x] Einstellungen on phones (jump links that wrap): the section tabs have no active underline and are cut at the edge.
- [x] Gegner: back link "Zurück" without eyebrow (PageHeader now; the zone is the analysis'); the zone "Fernwurf / leeres Tor" mixes two
  situations (analysis data, already reported).
- [x] Dates: "29. Okt. 26" (Suche) and "29.10.2026" (Gegner): one format.

## Batch 6: the player's side (audit as a field player, local test account)

- [x] P1 Analyse: the "Übungen" link on a weakness insight leads players to a 404 (drills are staff
  only) -> staff only. The 404 seen was a wrong test URL outside a club (product brand, fine).
- [x] P1 Start: "Zu erledigen: Nichts offen" while a self-assessment is waiting; the big stage is
  spent on "Keine Termine" -> the waiting self-assessment leads the stage and is a to-do.
- [x] P1 Match page: a player sees the coach's tools (comment field, drawings, spotlight, keys,
  defence systems) -> players get comments, clips and drawings to watch, no tab row, no court
  or defence systems (commenting stays: players may comment by design).
- [x] P1 Feed item: "Zuerst deine Einschätzung" but "Weiter" is the strongest button.
- [x] P1 Season: figures contradict the fixtures (season counts one match; xG 3.4 for 26 goals):
  backend, already reported. No xG sentence when goals and xG differ by more than double
  (`lib/voice.ts`, tested); the season counting itself stays with the analysis session.
- [x] P2 Feed item: title names no match; "Kommentare des Trainers" -> "Notizen"; green pill as
  decoration; rating scale without anchors.
- [x] P2 Kader for players ("Du" on the own row still open): "Verknüpft" is staff wording; "Rechts" without "Wurfhand"; own row "Du".
- [x] P2 Profil ("Paraden" for field players still open): missing consent as an error alert; form editable while it cannot go public;
  "Paraden" for a field player.
- [x] P2 Aufgaben and Termine empty states without a sentence on who sets them.
- [x] P2 Einstellungen: the 2FA admin sentence shown to players.
- [x] P3 Spielplan: "Alles Demo-Spiele"; score emphasis on the winner instead of the own team.
- [x] P3 Einwilligungen: guardian wording ("Du selbst") for an adult player (the tag only shows for a child).

## From the analysis session (API additions, see `docs/plans/ui-match-workspace.md` on main)

- [x] Web texts for the new notification kinds (join and access requests, official suggestions,
  official report), and a plain fallback for any kind without a text.
- [x] Official team search and claim: onboarding starts with "Mannschaft suchen" (grouped by club,
  take over, ask for access, join as a player; a club by hand stays one click away).
- [x] Suggestion inbox `/teams/{team}/official`: squad to confirm with numbers (duplicates flagged,
  players without a game unticked), "Statistik anzeigen" (`roster_stats`), reports to import,
  schedule changes with the plan lock, the table; a line on the squad page leads there.
- [x] Join requests (`/teams/{team}/join-requests`: "Passt zu #22 … im Kader?" links the account
  to the squad entry), access requests and the club verification in a settings section "Offizielle
  Daten" (`/settings/access-requests` leads there).
- [x] A quiet "Verein noch nicht bestätigt" line on the overview for admins, linking to the ways.
- [x] `PUT /kickoff` with `clock_s` for clips that start mid-half: "Uhr eintragen" in the throw-off step
  ("Spieluhr zeigt hier 12:40" at the paused moment, `lib/match-workflow.ts` `parseClock`, tested).
- [x] Shot zone split: "Fernwurf" and "Leeres Tor" (`empty_goal`) in the web texts.
- [x] Search hits outside the video come with null windows ("ohne Video" already handles it).
- [x] nuLiga/HLA report links (hint and error text); `roster_stats` toggle (in the inbox).
- [x] `no-video` errors on clip slides; referee kit (see "Open after PR 8").

- [x] Shot candidates (`shot-candidates`): a "Würfe" tool beside the events. With a report most
  moments come with its entry: Enter takes it (player and outcome pinned to the video); otherwise
  1 / 2 for the team and the tagger's letters G, S, M, P, B for the outcome; X no shot, U undo.
  Filter "Mit Matchbericht" first, the report counted against the video (`lib/shot-candidates.ts`).

## Open after PR 8 (for the next UI session)

State on 2026-11-09: PR 8 is merged into main. Still open from the analysis session's list and from
this round, in rough order:

- [x] `no-video` (422) on clip slides of a match without video: a readable message in the
  presentation editor instead of the generic error (`errors.no-video`; the scene search already
  offers no slide for hits without video).
- [x] Referee kit: `kit_referee` shows wherever the four team kits show (match create and edit
  through `KitFields`, the analysis colours in the workspace).
- [ ] Matrix `season_ids` (outdated: the API has it now, see the work queue at the top);
  build the season choice once the analysis session adds it.
- [x] Shot review: e2e `shots.spec.ts` (real upload, the candidate list from a recorded fixture);
  the timeline's signal ring follows the active shot candidate.
- [x] Official data screens: e2e `official.spec.ts` (search, claim, access and join requests, the
  suggestion inbox) with answers recorded by hand with invented names (`e2e/fixtures/official.ts`).
- [x] Screenshot review round (METHOD.md) for the new screens: onboarding search, the official
  inbox, the court from the hall, Würfe, Anwurf (scores and what is left in `PROGRESS.md`). Join and
  access requests in the settings and the overview line were not in this round.
- [x] The court step's "Passt" / "Neu markieren" pair for a court taken from the hall, beside the
  hall image with the court in orange; the step stays open until then (`courtUnconfirmed`).

## Later (features)

- [x] Opponent profile: home or away per game (`is_home`), xG only with enough shots with a position
  (`xg_coverage` at least 0.7, `lib/xg.ts`, also on the match stage, the analysis overview, the
  season rows and the season's xG statement).
- Player: one next-action list (self-assessments, assignments, replies to dates); personal season
  line linked to clips; read-only drills a coach assigns. Done: "Meine Szenen" on the match page
  (assessment first, then the scenes; e2e `player.spec.ts`).
- Own drills ("Neue Übung"): needs a drills API; the library is static today.
- Player status (verletzt, abwesend) on the squad; attendance on units and dates; assignment
  progress ("8 von 14 erledigt"); recurring training slots; a team consent table for staff.

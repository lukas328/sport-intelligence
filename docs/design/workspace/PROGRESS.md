# Progress: match workspace rework

Branch `claude/exciting-franklin-g1ecgw` from `identity/halle` with `vision/real-footage` (PR 3)
merged in. Method: `METHOD.md`; references and rubric: `REFERENCES.md`. Screenshots of each round
are taken on the local stack (demo club, a 1-minute synthetic clip placed at 12:40 of the first
half, 45 test goals of an official report, 6 goal candidates) and are not committed.

## Slice 1: structure (before the review rounds)

- Work steps above the video (court, throw-off, goals, players) with what is still open; tools
  (events, defence systems, notes) after them. The first open step shows first.
- Player and the active step side by side, both sticky on desktop; on phones the player sticks
  under the top bar and the step follows it.
- Match timeline under the player; counts read against what the video covers.
- Full-screen goal review: one candidate after the other, the clip plays itself.

## Round 0 (fresh-eyes review of slice 1)

Scores (desktop light): anchor 3, signal 3, hairlines 3, game language 2, team by side 2,
numbers to video 2, review speed 2, proposed vs confirmed 2, type 3, edge states 3.
Main findings: contradicting counts, file time instead of match clock, decision buried in a form,
32 identical selects with jargon, chrome below the video, timeline as a status graphic, events as an
admin form, wrong throw-off state for a clip that starts mid-half.

## Round 1

Changed: match clock everywhere and on the picture, agreeing counts, keys on the buttons and a
status line, throw-off of a clip, people in order of appearance, cameras and quality in the court
step, timeline as a scoresheet (sides, rings and filled marks, zoom "Moment" and "Spiel"), phone
order, events laid out like a match sheet.

Scores: anchor 3.5, signal 2.5, hairlines 3.5, game language 4, team by side 2.5, numbers to video 3,
review speed 2.5, proposed vs confirmed 3, type 3.5, edge states 3.

## Round 2

Changed: the current candidate and its answers first with a visible undo, "2 von 5"; the signal
moves to the candidate on the axis when its step is open; recorded candidates filled; taller sided
lanes and a notes lane; people as play buttons with the read shirt number; no wrong "Hier setzen";
the court step in one sentence with technical details folded; the mini court follows dark mode.

Scores: anchor 3, signal 4, hairlines 3, game language 4, team by side 3, numbers to video 3,
review speed 4, proposed vs confirmed 4, type 4, edge states 3. Desktop passes the rubric's rule
(no score below 3 on anchor, signal, review speed); phone did not (video and decision not on one
screen, no timeline in view).

## Round 3 (last review round of this slice)

Changed: on phones the decision sits right under the sticky player and the stage keeps only the
score; an events lane on the axis; recorded candidates as squares, confirmed goals as dots; R
replays; the undo hint shows before the first decision; people anchored as "Person 9 · 60 s im
Bild"; after the review the moment carries the signal stroke on phones, short tracks fold away,
B tags a blocked shot, the axis centre line is stronger.

Scores (desktop / phone): anchor 4 / 3, signal 4 / 2 (fixed after the review), hairlines 4 / 4,
game language 4 / 4, team by side 2 / 2, numbers to video 3 / 3, review speed 4 / 4, proposed vs
confirmed 4 / 3, type 4 / 4, edge states 3 / 3. Desktop ready; phone ready after the signal fix.
The slice is closed after three rounds as the method says; the rest goes to the open list.

## Slice 2: Analyse tab

Test data on the local stack for this slice: a coherent 26:18 (44 goals of the official report with
scorers, about 60 hand-tagged shots, saves, turnovers and suspensions), not committed.

- A1 (review: no sub-tab ready; the voice said nothing true, a minute of video as loud as the
  score, keepers as KPI tiles, raw keys): basis line with sources and coverage, a sentence when the
  events do not add up to the result, empty rows left out, scorers list, "Was auffällt" with one
  signal, match report on hairlines, possession and attacks also with events.
- A2 (review: keepers +3 on hairlines; overview Q7 3; shots and report still without a signal):
  three insights with a win opening on what worked, figures in ink with a dotted underline, the
  video block as one line, keepers as one sheet with German zones, no empty court, shirt number
  once, share button icon-only on phones, physical load with team names and its coverage.
- A3: one statement of what decided the match from the head-to-head figures
  (`lib/match-decided.ts`, tested), one resin mark per sub-tab (weakest shot zone, keeper's weakest
  zone, most turnovers), zones as hairline rows, a readable goal picture.
- A3 review (last round): overview Q7 4 (the statement of what decided the match), hairlines 4 on
  shots and keepers, but the overview had no signal left and physical load overflowed on phones.
  Fixed after the review: the overview's signal sits on the counted row the opponent won most
  clearly (after a win the thing to work on), the statement leads to its scenes, the goal picture
  fill is visible in dark mode and has a one-line key, physical load sits on an open sheet without
  the doubled sentence and fits 390 px, the sub-tab row fades at the edge on phones. Slice closed.

Still open in the analysis: goal cells and the keeper table do not open scenes yet; a one-line
reading above shots and keepers ("Mia Meier hielt oben links 3 von 4").

## Slice 3: Szenen tab and feedback

Test data: scenes inside the short clip, consents for the squad except two players, one coach note.

- S1 (s0 was cards inside cards with a comment form under each of 25 scenes): per-player blocks on
  rules, one line per scene with the match clock, notes on request, saved notes in handwriting;
  hairlines 1.5 to 4. Not ready: no video on the page, no signal, no progress.
- S2: "Feedback" became a tool of the video workspace (scenes beside the docked player); a queue
  line ("Notizen 1 von 25 · weiter mit ...") with the signal on the next player; squad order;
  scrubber marks in one ink; reels first on the tab. Review: feedback tool ready (anchor 4,
  signal 4, speed 3); the scenes tab still cold (anchor 2, signal 1).
- S3 (last round): the tab opens with the feedback state, the next player with the signal, a
  "Weiter mit ..." button into the tool and the latest real coach note in handwriting; reels not
  ready yet show their frame in the real format; positive and to-learn as words, not fill and
  ring (those mean proposed and confirmed in the workspace); "Notiz" visible on every row.

Backend findings (analysis session): feed generation crashes on events outside the video (a clip
from mid-half has negative or too large video times; such events should be skipped); the API
queues `handball_worker.export.run_highlight_reel`, which lives in `handball_worker.reels`, so
reels never render (the test patches the same wrong path).

## Slice 4: entry pages (Spielplan, Übersicht, Saison)

- P1: fixture list on rules with S/U/N squares and the score in ink. Review: fixtures hairlines 5
  but no signal and nothing to do; overview's yellow mark contradicted the match page (same
  insights, other order and marks); onboarding was the loudest button; season phone layout broke.
- P2: overview insights in the match page's order and marks, quiet onboarding, verbs for empty
  next steps, no filler state line; fixtures count the matches without video and mark the newest;
  demo said once; S/U/N squares aligned; season form squares stay square, "Das letzte Spiel.";
  `.sheet` tables open under a rule everywhere.

- P2 review: overview and season ready, fixtures ready on desktop but names cut on phones and the
  signal on a status. P3 (last round): names wrap and are never cut, the meta line stays short on
  phones (no competition), the marked row says "Video hochladen", an "Kommend" line with "Spiel
  ansetzen" when nothing is scheduled, the season table's sticky column on the page background
  with a hairline, "1 Tor" in the singular, insight rows on the overview with an arrow. Slice
  closed.

Data/API (season): the season counts only matches with events (1 instead of 5 with a result) and
adds goals from the report and from tagging (31 against 26:18 on the match page, which counts each
goal once). Season figures should use one source per match, like the match statistics.

## Consistency pass across the slices

A last fresh-eyes review over all three tabs looked for seams between the slices. Fixed: one
signal form (the marker stroke, also in the step row; it was a filled chip there), a signal on the
first open report goal in the goals step, no pink row in physical load and the heatmap in ink,
clip marks on the scrubber as ticks (squares mean recorded goals on the timeline), team names
instead of "Wir / Gegner" on the stage and in the timeline legend, "Matchbericht" everywhere
(the sub-tab said "Matchreport"), the comment tool called "Kommentare" (so "Notizen" means only
feedback notes), quiet secondary buttons for the same kind of action, the goal step's list switch
as an underline toggle, the "Moment" axis with the half ("1. HZ 12:40").

## Open

- Data/API (for the analysis session): an insight files the goalkeeper with a 44 % save rate as a
  weakness ("14.8 Tore unter Erwartung" against an xG of 3.2); xG 3.4 for 26 goals; the shot-zone
  "Fernwurf / leeres Tor" mixes two situations; the goal picture adds up to 35 of 39 shots; sprint
  counts and top speeds of 31 to 32 km/h from one minute look implausible.

- Done (2026-11-09): the sided lanes carry the team names at their right end (own above, opponent
  below); the legend in the caption stays for screen readers.
- Done (UI session, 2026-11-09): the control bar shows the match clock once the throw-off is set;
  on phones it sits under the picture instead of over it.
- Event keys are English mnemonics (G, S, M, P, T); German letters would collide (T for Tor and
  Ballverlust), so they stay until a coach asks.
- Goal candidates counted as "schon erfasst" by the API can match a report goal just before the
  clip starts (12:26 for a clip from 12:40): the matching window of the analysis, to raise with the
  analysis session.

- Analyse tab (next slice): possession, attacks, physical load, shots in the same language.
- Closed (2026-11-09): "Teilen" and "…" sit as icon buttons in the row of the tabs at 390 px.
- Dev only: a hydration warning appears once after hot reloads (stale server bundle), not on a
  fresh start.

## Backend findings

For the analysis session; read from this branch. Newest first.

- 2026-11-09 (helper, branch `helper/invite-roster-link`, no migration): invited players were
  linked to their roster entry only when the invitation named it (`player_id`), and the invite
  form sends `player_id` for parents only, so an invited player saw no dates and none of their
  own views. The API now:
  1. `POST /v1/orgs/{org_id}/invitations` takes `player_id` for player and goalkeeper
     invitations too (the UI should offer the roster entry like the child for parents; 409
     `player-linked` if the entry has another account). Without `player_id`, optional
     `first_name`, `last_name`, `jersey_number` pick the entry when they match exactly one entry
     of the team's current season without an account; the response's `player_id` says whether
     one was found (null: link later).
  2. Accepting an invitation without an entry (onboarding, e-mail only) links the one free entry
     whose full name is the account's name; an entry with another account answers 409
     `player-linked` on accept and is never taken over.
  3. Join requests: unchanged, approving with `player_id` (or the suggested match) links it, 409
     `player-linked` if taken.
  4. Staff link or unlink later: `PUT /v1/orgs/{org_id}/teams/{team_id}/players/{player_id}/account`
     with `{user_id}` (a member of the team, not a parent: 422 `parent-not-player`; 404 for non
     members; 409 `player-linked` if another account holds it) answers `{player_id, user_id,
     name}`; `DELETE` on the same path unlinks (204). Roster entries carry `account_user_id`
     (staff only, null for others), to show whom an entry belongs to against the team members.
  Parents stay separate: a parent invitation with the child creates a guardianship; the child's
  account link is not touched.
- 2026-11-09 (helper, branch `helper/squad-status-progress`): wishes 1 and 2 are built in the API
  (migration 0036), the client is regenerated; no UI yet.
  1. Player status: `PUT /v1/orgs/{org_id}/teams/{team_id}/players/{player_id}/status` with
     `{kind: "injured" | "absent", until?: date, note?: string (max 140)}`, `DELETE` on the same
     path means fit, `GET /v1/orgs/{org_id}/teams/{team_id}/player-statuses` lists the statuses in
     force. The roster (`GET .../seasons/{season_id}/roster`) carries `status` per entry
     (`{player_id, team_id, kind, until, note, updated_at}` or `null` for fit). Staff (coach,
     analyst, goalkeeper and athletic coach, team manager, club admins) read and set; players see
     only their own `status` in the roster. `until` counts to the end of that day (Swiss time);
     after it the status reads as `null`; an until-date in the past is a 422.
  2. Assignment progress: `GET /v1/orgs/{org_id}/teams/{team_id}/assignments` and the new
     `GET /v1/orgs/{org_id}/assignments/{assignment_id}` (staff who may assign) carry `recipients`,
     `done`, `progress` (every recipient: `user_id`, `name`, `player_id` or `null`, `seen_at`,
     `done_at`) and `still_open` (the same, only those not done, by name). "8 von 14 erledigt" is
     `done` of `recipients`. For players (`/me/assignments`, `PUT .../status`) `recipients` and
     `done` cover only their own status (1 and 0 or 1); `progress` and `still_open` are `null`.
- 2026-11-09 (analysis helper, branch `helper/analysis-plausibility`): the implausible figures,
  checked against the synthetic ground truth of the demo video.
  1. Physical load: the computation smoothed before it filtered jumps, so a track taking over a
     neighbour 2 m away (identity switch in an occlusion) read as three steps of 9 to 10 m/s;
     it also counted the tracker's predictions and took a 400 ms peak as top speed. Now jumps
     and gaps are found on the raw positions, only observed points count and the top speed must
     be held for 1 s (`handball_vision.physical`). On the demo video: top speed 34 km/h before,
     25 km/h now (truth 23.4). The team row's top speed is the fastest player's, as intended.
  2. Demo data itself was unrealistic: the synthetic default turns the ball over every 12 s with
     the whole team sprinting across the court (about 190 m per minute per field player, 30
     sprints per team and minute, a fast break in every attack). `scripts/seed.py` now renders
     with `--demo` (goals and throw-offs, 25 s attacks, jogging between positions, sprints only
     in counters): about 100 m per minute, a few sprints. Run `make seed` again for new figures.
  3. Fast breaks: an attack opened by the team's own throw-off counted as a fast break when the
     team walked up quickly from the centre line; it no longer does. "4 of 5" was correct for
     the old demo video (four turnovers with a full sprint each).
  4. Distances of the white kit stay about a third too high on the demo video: ghost and duplicate
     tracks (7.9 tracks per frame for 6 field players), a tracking issue, not the metric. The UI
     team row sums every track of a side, so it inherits them; the player rows do not.
  5. Goalkeeper: GSAx was computed over the shots with xG, but positions come mostly with goals
     (overlay, tracking, matched report goals), rarely with saves; over goals alone xG is always
     below the goals ("14.8 Tore unter Erwartung" at 44 % saves). `gsax` is now null unless at
     least 70 % of the saves and of the goals have xG, and then no keeper insight is made.
     Match stats and season rows carry `xg_goals` (goals of the shots with xG): set xG against
     that, not against all goals ("xG 3.4 for 26 goals" compares xG of a few shots with every
     goal of the result). Season rows also carry `xg_against_coverage` and `xg_goals_against`;
     the season page shows `xg_against` and the voice's defence line without a coverage check.
  6. Goal candidates: a report goal whose video time lies before the clip (or after its end) no
     longer counts a candidate as "schon erfasst". The zone "Fernwurf / leeres Tor" was already
     split on main (`long_range` and `empty_goal`, zones spec version 2, alembic 0033); the
     metrics version is bumped, so cached statistics are recomputed.
- 2026-11-09 (backend check on main): three findings from the UI session were already fixed on
  main (the UI stack ran older code), nothing to change:
  1. Feed and events outside the video: `feed.generate` skips events before or after the video
     (`services/feed.in_video`, test `test_feed.py::test_in_video`).
  2. Reels: the API queues `handball_worker.reels.run_highlight_reel`; the job contract test
     (`test_job_paths.py`) checks every queued path against the worker sources and the payloads.
  3. Season figures: every match with a result counts, goals per match from one source like the
     match statistics (test
     `test_insights_api.py::test_season_counts_every_played_match_and_each_goal_once`).

- 2026-11-09 (UI session, demo data with a synthetic 1-minute video): 4 of 5 attacks counted as
  fast breaks; 33 and 60 sprints and 1.22 km against 2.02 km in one minute; a team row's top
  speed of 31.7 km/h (the maximum of one player?).

- 2026-11-09 (UI session): API wishes for the next UI features, none built in the UI yet:
  1. Player status on the squad (verletzt, abwesend, with an optional until-date), readable by
     staff; today a status exists only per training unit or match (`attendance`).
  2. Assignment progress for staff ("8 von 14 erledigt"): per assignment the count of players
     done and the list of who is open.
  3. Recurring training slots (weekday, time, place) that create the units of a season.
  4. A team consent overview for staff: per player the purposes consented, before filming.
  5. Own drills: create, edit, share within the club (the library is static today).
  6. A player's season line: per match their goals, shots, saves with links to the events.
- 2026-11-09 (UI session): the matrix takes `season_ids` (since 95132d3); the UI now offers
  "Saison" (this and last, one season, all). The earlier note below is outdated.

- 2026-11-09: the matrix has no `season_ids` filter in the API (`handball_metrics.query.Filter`
  knows `match_ids`, `last_n_matches`, opponent, ...; an unknown field is a 422). The UI list
  mentions it; nothing to build until the filter exists. The matrix page today counts all
  matches of the team.
- 2026-11-09: `calibration_error` is English free text (`str(exc)`); the UI uses
  `calibration_info.reason` instead and says each reason in de-CH, en and fr. A failed calibration
  without `reason` falls back to "court".

- 2026-11-09: **the zone check can be switched on.** The web texts now match the PDF texts
  exactly in de-CH, en and fr, including `zones.long_range` ("Fernwurf") and `zones.empty_goal`
  ("Leeres Tor"); the insight texts match too (checked against `report_pdf.TEXTS` after merging
  main). `apps/api/tests/test_report_pdf.py::test_insight_texts_match_the_web_app` can compare
  the whole `zones` block again (drop the `split` exclusion) once PR 8 is merged.
- Earlier, still open (see slice 3): feed generation crashes on events outside the video;
  `run_highlight_reel` is queued under `handball_worker.export` but lives in
  `handball_worker.reels`.
- Earlier, still open (see Open): the season counts goals from both the report and tagging;
  sprint counts and top speeds from one minute of video look implausible.

## Round after the merge with main (2026-11-09)

- Opponent profile: Heim or Auswärts per game; xG per match only when at least 70 % of the shots
  on target have a position, else "xG: zu wenige Würfe mit Position (5 von 12)". The same rule on
  the match stage, the analysis overview, the season rows and the season's xG statement.
- Throw-off step: "Uhr eintragen" sets the match clock at the paused moment (`clock_s`), for
  videos that start after the throw-off; the error for a time outside the half is in the texts.

## Review round over the new screens (UI session, 2026-11-09)

Screens: onboarding with the official team search (results, join form, after taking a team
over), the suggestion inbox "Abgleich mit handball.ch", the court step with a court carried over
from the hall (new: hall image with the court and "Passt" / "Neu markieren"), the Würfe tool
before and after one decision, the throw-off step. Desktop 1440 light and dark, phone 390. Test
data invented (the same fixtures as the new e2e specs `official` and `shots`); the analysis
answers were stubbed, so the "In der Warteschlange 0 %" card and the 2FA banner are artifacts.

Scores (1 to 5; anchor, signal, hairlines, game language, team by side, numbers to video, review
speed, proposed vs confirmed, type, edge states):
- Onboarding: -, 1, 4, 3, -, -, -, -, 4, 3
- Abgleich: -, 2, 4, 3, 2, 1, -, 3, 4, 3
- Spielfeld from the hall: 3, 2 (before Passt) / correct after, 3, 3, -, -, -, -, 4, 4
- Würfe: 2, 2, 3, 3, 3, 1, 3, 2, 3, 2
- Anwurf: 3, 2, 4, 4, -, -, -, -, 4, 4

Fixed after the review:
- The official table is shown in the order of its ranks (`standingByRank`, tested), not in the
  order the rows arrive.
- Würfe: both team choices are drawn as choices (the unselected one looked like text); the
  buttons of the decision are 44 px on phones; key letters only where there is a fine pointer.
- Würfe: the timeline's candidate lane shows the shot moments while shots are reviewed, with the
  signal ring on the one that is up (as for goal candidates).
- Court step: the team colour legend shows only with the mini court it explains.
- Found by the new e2e (axe): the small "Aus dem Matchbericht übernehmen" label on the accent
  button was faded to 80 % (4.2:1); no longer faded.

Checked and not changed:
- "The report card fails contrast in dark mode": it is dark text on the light accent (about 6:1).
- "0 im Video bestätigt" after a decision and "21 liegen ausserhalb" without a throw-off came from
  the stubbed list (it did not recount the report); the API recounts on the refetch.

Left open (next round):
- Würfe: moving to the next moment does not seek the video (the goal review does it in its full
  screen mode); a "R"/play per row exists. Seek with pre-roll on each advance is the next step.
- Würfe without a throw-off: the times come from the report's clock map; say "laut Matchbericht"
  until the throw-off is set, or gate the tool behind the Anwurf step (product decision).
- Report entry wording: "Parade, #14 …" does not say that #14 is the shooter; the analysis
  session's report line names the shooter, the keeper is not in it.
- Phone: the work strip of four steps and four tools scrolls sideways and cuts the last label;
  the bottom navigation covers the end of the step panel.
- Onboarding: progress segments in light mode are nearly invisible; a player joining sees the
  coach's "Schritt 1 von 4"; "@ HSG Rheinau" in the inbox (away games) reads as an anglicism.
- After "Passt" the workspace stays on the court step instead of moving on to the next open step.

## Round 2 over the new screens (UI session, 2026-11-09)

Decisions taken in the session (the owner left them to it):
- Würfe stay open without a throw-off: the moments are video times, only the game times are
  the report's estimate. A line says so and links to the throw-off step.
- Each moment that comes up is shown in the video, paused at its lead-in.
- After "Passt" on a court from the hall the workspace goes to the next open step.

Changed:
- The report's entry names the shooter: "Parade, Wurf von #14 …".
- Official inbox: "gegen X" and "auswärts bei X" instead of "@ X".
- The `.club` scope rule moved to `@layer base`. Before, it beat the utilities on the same
  element: the onboarding header showed the page paper instead of the club colour (the progress
  bars white on paper, the finding "progress invisible"), and the confirm dialog, the bell and
  the command palette showed paper instead of the raised surface. The open onboarding steps are
  no longer faded (white at 75 % on the club colour is below 4.5:1).
- Referee kit checked: in the create and edit forms (`KitFields`) and in the analysis colours.

Checked, not a problem: "the bottom navigation covers the step panel" and the floating bars in
the phone captures come from full-page screenshots; the page keeps 112 px free under the content.

Still open: the phone work strip scrolls sideways and cuts the last visible label (a scroll
affordance, kept); a player joining from the team search sees the coach's "Schritt 1 von 4".

## Review of the remaining official-data screens (UI session, 2026-11-09)

Join requests, the settings section "Offizielle Daten" (verification, access requests) and the
overview line for an unverified club, desktop light and dark and phone, invented data.

- The overview line "Der Verein ist noch nicht bestätigt …" was never visible: the stage pulls
  itself up to the top edge and covered it. It is now passed into the overview and sits right
  under the stage.
- Join requests and the official inbox showed the team header ("Kader") above their own heading
  once they belonged to Team · Kader; the team header now steps aside on these two pages.
- The settings section reads well: ways to confirm the club with the club's mail domain, access
  requests with "Als Trainer/in aufnehmen", "Als Vereinsadmin aufnehmen" and "Ablehnen".

## Autonomous round (UI session, 2026-11-09)

The owner asked the session to decide on its own. Done in this round, each with tests:
- Navigation: the official data and the join requests keep Team · Kader; an opponent keeps
  Spiele · Spielplan.
- Consents: no "Du selbst" on the own profile; "Dein Kind" stays for a child.
- Onboarding: a player who asked to join no longer sees the coach's four steps.
- Phones: the video controls sit under the picture (they covered the lower half of the frame);
  keyboard hints are hidden for touch input; the work strip fades at its edge while more tabs
  follow.
- Overview: the line for an unverified club was hidden under the stage; it now sits under it.
- Players: "Deine Szenen" on the match page (assessment first, then the scenes); dates after the
  next one without a reply count in "Zu erledigen".
- e2e: `player.spec.ts` (match page and overview of a player); the court from the hall with
  "Passt" in `shots.spec.ts`.

## Analyse tab review round (UI session, 2026-11-09)

Demo club from `scripts/seed.py` (synthetic 1-minute video, no events counted), all sections,
desktop light and dark and phone, reviewed with fresh eyes against `REFERENCES.md`.

Scores before the fixes (anchor, signal, hairlines, game language, team by side, numbers to
video, -, estimated vs confirmed, type, edge states): Übersicht 2, 1, 4, 3, 3, 3, -, 3, 4, 4;
Matchbericht, Würfe, Torhüter 1, 1, 4, 2, 3, 1, -, 3, 4, 1; Laufleistung 1, 1, 3, 2, 2, 1, -, 3, 3, 3.

Fixed:
- Without counted events, Matchbericht, Würfe and Torhüter silently showed the video overview
  under their own tab. They are no longer offered then; the overview says how they come (import
  the match sheet, which is now the primary button, or mark courtside).
- Sections in the order of the match sheet: Übersicht, Matchbericht, Würfe, Torhüter,
  Laufleistung.
- Possession: "Ballbesitz" next to each team's share; the header reads every figure against the
  video ("Aus 1:00 Video von 60:00 Spielzeit, geschätzt aus den Positionen"); attack rows carry a
  play mark and are 44 px tall, the helper sentence about clicking is gone.
- Laufleistung: "Höchsttempo" (not "Topspeed"), "Aufenthaltsorte" (not "Heatmap"), metres in
  de-CH format (1'463 m), "Erfasst" right after the name so the coverage stays in view on phones,
  "Hohe Intensität" only from tablets up; the overview link says "Laufleistung ansehen".

Left open: the attack strip and list use video time until the throw-off is set (honest, but the
coach thinks in game time); team rows of the physical table select the map but do not lead to the
video; the data notes for the analysis session (4 of 5 attacks counted as fast breaks, 33 and 60
sprints in one minute, a team's top speed of 31.7 km/h) are in "Backend findings".

## Phone round over the match workspace (UI session, 2026-11-09, after PR 18)

Real phone emulation (Pixel 7, touch), viewport captures of the court from the hall, the goal
candidates and the shots, inline and in the full-screen review; fresh-eyes review.

Scores (anchor, signal, hairlines, game language, team by side, numbers to video, review speed,
proposed vs confirmed, type, edge states): court 3, 2, 3, 4, -, -, 2, -, 4, 3; goals inline 3, 2,
3, 4, 3, 4, 2, 3, 4, 4; goal review 4, 4, 4, 4, 3, 4, 4, 3, 4, 4; shots inline 3, 3, 3, 4, -, 2, 2,
3, 4, 4; shot review 4, 4, 3, 4, 3, 3, 3, 3, 4, 4. Both full-screen reviews fit video and decision
on one screen.

Fixed:
- Court from the hall: "Passt" and "Neu markieren" sat under the bottom navigation; on phones they
  are now a fixed bar above it (thumb zone) until the court is checked. The orange court lines
  have a dark halo, so they stand out on a wooden floor.
- Goal candidates: key letters hidden for touch input (as for shots), all four answers at least
  44 px, "Nochmals" an outlined button (it looked disabled).
- Shots: "Kein Wurf" and "Nochmals" outlined buttons instead of bare text.

- Shot review: one count ("1 von 1 mit Matchbericht · 2 weitere offen") instead of "1 von 1"
  next to a tab saying "Offen (3)".

Left open: the hero and the tab row above the workspace on phones (collapse while reviewing);
the dense report sentence above the shots as a row of tappable counts.

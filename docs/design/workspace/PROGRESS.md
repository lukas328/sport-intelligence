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

- Team by side on the axis still reads weakly (2): a lane label per side ("H1" / opponent) would
  make it explicit.
- Done (UI session, 2026-11-09): the control bar shows the match clock once the throw-off is set;
  on phones it sits under the picture instead of over it.
- Event keys are English mnemonics (G, S, M, P, T); German letters would collide (T for Tor and
  Ballverlust), so they stay until a coach asks.
- Goal candidates counted as "schon erfasst" by the API can match a report goal just before the
  clip starts (12:26 for a clip from 12:40): the matching window of the analysis, to raise with the
  analysis session.

- Analyse tab (next slice): possession, attacks, physical load, shots in the same language.
- Phone: "Teilen" and "…" take their own row under the tabs.
- Dev only: a hydration warning appears once after hot reloads (stale server bundle), not on a
  fresh start.

## Backend findings

For the analysis session; read from this branch. Newest first.

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

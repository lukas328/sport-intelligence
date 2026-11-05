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
- The player's control bar shows video time while the picture shows the match clock; on phones it
  covers the lower half of the frame.
- Event keys are English mnemonics (G, S, M, P, T); German letters would collide (T for Tor and
  Ballverlust), so they stay until a coach asks.
- Goal candidates counted as "schon erfasst" by the API can match a report goal just before the
  clip starts (12:26 for a clip from 12:40): the matching window of the analysis, to raise with the
  analysis session.

- Analyse tab (next slice): possession, attacks, physical load, shots in the same language.
- Phone: "Teilen" and "…" take their own row under the tabs.
- The video player's own control bar on phones covers half the frame.
- Dev only: a hydration warning appears once after hot reloads (stale server bundle), not on a
  fresh start.

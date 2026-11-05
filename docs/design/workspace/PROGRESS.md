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

## Open

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

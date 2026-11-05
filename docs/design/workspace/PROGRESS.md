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

Scores: see the round 2 review below once it is in.

## Open

- Analyse tab (next slice): possession, attacks, physical load, shots in the same language.
- Phone: "Teilen" and "…" take their own row under the tabs.
- The video player's own control bar on phones covers half the frame.
- Dev only: a hydration warning appears once after hot reloads (stale server bundle), not on a
  fresh start.

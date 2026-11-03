# 020. Automatic event baseline from tracks, highlights, teams from formations

- Status: accepted
- Date: 2026-11-03

## Context
Principle P1 (automatic first) and the P0 features highlights, player feed and preparation report
need events without manual tagging. The pipeline tracks players but has no ball tracker yet, and no
real labelled handball footage is available in this environment (Q-ADD-6, Q-DATA-1).

## Decision
- **What is detected from player positions only** (`handball_vision.events`):
  - sides from the goalkeepers (majority over 20 s); a lasting flip is a side change;
  - possession phases: one team's field players in the attacking half while the other team's are
    back home (min. 2 s);
  - throw-offs: one team in its own half with a player at the centre point, the other team in its
    half, median per-track speed below 1.5 m/s for at least one second (one outlier per team
    tolerated);
  - goals: a throw-off that does not open a half means the other team scored at the end of its
    preceding attack (confidence = min of both, times 0.85);
  - pauses (fewer than 4 field players for 45 s) and match boundaries (pause of 90 s or more, then a
    throw-off) as suggestions for tournament videos.
- Shots, saves, turnovers and blocks are **not** guessed; they need the ball and stay with tagging,
  imports and a later trained model. The UI says so.
- The API stores the results with source `heuristic` and their confidence, replaces them on a
  re-analysis, never duplicates a goal a person entered (5 s window), sets the match clock from the
  opening throw-offs when nobody did, and uses the possession phases instead of the event-based
  estimate.
- **Team assignment second signal:** at throw-offs both teams stand in their own half; tracks seen
  there vote for the team defending that half. Only uncertain colour labels (< 0.75) are changed,
  with at least 5 votes and 80 % agreement.
- **Highlights** are selected by rules (type weight, late phase, close score, fast break, variety)
  from events with confidence of at least 0.6 and rendered by the worker (intro card, 16:9 or 9:16
  with a crop following the median of the players, smoothed over 1.5 s, burned-in spotlight, name
  strip, no music). Consent is checked per featured player.

## Consequences
- Measured on synthetic matches through the full pipeline (`docs/perf/events-eval.md`); real
  footage (TeamTrack handball, UWB amateur positions, the club's own matches) is needed before the
  numbers mean anything for production. The dataset hosts are blocked in this environment.
- A goal right before half-time cannot be inferred (the next throw-off opens the half).

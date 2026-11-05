# Report: match workspace and the pages around it

Branch `claude/exciting-franklin-g1ecgw`, based on `identity/halle` with `vision/real-footage`
(PR 3) merged in. Handover: `docs/plans/ui-match-workspace.md`. Method: `METHOD.md` (rounds with a
fresh-eyes review against `REFERENCES.md`). Round log with scores: `PROGRESS.md`.
Screenshots: `screens/` (before and after, local stack with test data).

## What changed

### Video workspace (the match page's "Video" tab)

- **Work steps instead of a stack of cards.** One row above the video: court, throw-off, check
  goals, assign players, each with what is still open; then the tools: events, defence systems,
  notes, feedback. The first open step is shown first.
- **The player stays in view.** Player and the active step side by side, both sticky on desktop;
  on phones the player sticks under the app bar and the step follows it directly.
- **Match clock everywhere.** "1. HZ 12:55" on rows, comments, the player's controls and the
  picture; video time only while no throw-off places the video on the match clock.
- **Counts read against what the video covers.** Goals before or after a clip are outside, not
  missing, and are not counted as open.
- **Goal review.** The current candidate first ("Tor?", suggestion, 1 / 2 / X / R, "2 von 5"),
  a status line with a visible undo, a full-screen review mode in which each clip plays itself.
  Rejected candidates stay stored as before.
- **Match timeline.** Video coverage, report goals, candidates, events and notes on one axis;
  own team above the centre line, the opponent below; rings are proposals, filled marks
  confirmed goals, squares goals already recorded elsewhere; zoom "Moment" and "Spiel".
- **Steps in plain words.** Court in one sentence with a real "neu ausrichten" button; throw-off
  that never offers a wrong "Hier setzen"; people in order of appearance with the read shirt
  number; events laid out like a match sheet with the key on each button.
- **Feedback.** The players' scenes beside the player, a queue ("Notizen 1 von 25 · weiter mit
  ..."), coach notes in handwriting.

### Analysis tab

- One statement of what decided the match from the head-to-head figures
  (`lib/match-decided.ts`), with links to its scenes.
- A basis line: where the figures come from and what the video covers; a sentence when the events
  do not add up to the result.
- Three insights, a win opening with what worked; one signal per sub-tab; figures in ink with a
  dotted underline where they open scenes.
- Goalkeepers as one match-sheet table; shot zones as hairline rows; a readable goal picture;
  physical load with team names and its coverage.

### Scenes tab, fixtures, overview, season

- Scenes: the feedback state first (next player, latest coach note), reels in their real format.
- Fixtures: on rules, results as form-guide squares, the open work counted and the next action
  marked, an "upcoming" line when nothing is scheduled.
- Overview: insights in the match page's order and marks, quiet onboarding, next steps as verbs.
- Season: form squares stay squares on phones, open sheet tables.
- Kit colours as small shirts.

## The rule set that holds it together

- One resin signal per screen, on the thing to act on.
- Fill and ring mean confirmed and proposed; words, not marks, for positive and to-learn.
- Ink for figures, red only for goals against and errors; a dotted underline means "opens scenes".
- Hairlines and rules, no cards; underline tabs at the second level.
- Match clock as the coach says it.

## Checks

- `pnpm lint`, `pnpm typecheck`, `pnpm test` (112 unit tests) green.
- E2E on the local stack (chromium and mobile): match, analysis, layout (no horizontal scroll at
  390 px), courtside marks, data, training green, including axe. Specs that need Mailpit or the
  operator domain (account, family, onboarding, ops) cannot run on this stack.

## Open, and for whom

See `PROGRESS.md`, section "Open". In short:
- **Analysis and backend:** feed generation crashes on events outside the video; reels are queued
  under a wrong worker path; the season counts only matches with events and adds report and tagged
  goals twice; insight and xG values on the test data look wrong; the goal-candidate matching
  window reaches before the clip.
- **App:** a server-render warning after sign-in in AppShell (suggested as a separate task); the
  player's own control bar on phones; goal cells and the keeper table do not open scenes yet.

# Metric definitions (BRIEF 4.8)

All metrics are computed from events and possessions (`handball_metrics.compute_match_stats`) and never
stored as truth; caches carry the metrics version and are recomputed when events change. Positions are
normalised so the attacked goal is at x = 40 (`packages/court`).

| Metric | Definition |
|---|---|
| Goals (one source each) | With an imported official report (`source = official_report`) its goals are the match's goals: a goal of another source on the same side within 20 s of match clock of an official goal is that goal (nearest pairs, one per source and official goal) and does not count again; the official goal takes over its position, zones and scorer. Automatic goals (heuristic, model, overlay, confirmed candidate) without an official counterpart count only with `attributes.review = confirmed`. Same rules as `official_report.apply` at import time (`stats.one_source_per_goal`). |
| Shots | Shots with outcome goal, save, miss or post. **Blocked shots are excluded** and reported separately (`shots_blocked`). |
| Shooting % | goals / shots (as above). |
| Saves (team) | Opponent shots with outcome `save`. |
| Save % | saves / (saves + goals against). Misses and posts are not shots on target and are excluded; posts are reported separately. |
| Attack efficiency | goals / possessions. Shown only when possessions are known. |
| Turnover rate | turnovers / possessions. |
| Turnovers by type | bad_pass, catch_error, steps, double_dribble, offensive_foul, line_violation, passive_play, other. |
| 7 m | `seven_m_awarded` from events of that type; 7 m shots and goals from shots with `shot_type = penalty`. |
| Shot zones | `zones.json` (version 2) via `zone_of`: 7 m, fast break, **empty goal** (`shot_type = empty_net`, any distance; also for rows stored before the split), else from the position, **long range** beyond 15 m. Up to metrics 0.2 empty-goal shots were part of long range ("Fernwurf / leeres Tor"). |
| Fast break goals | Goals with zone `fast_break` (shot within 6 s after gaining possession, `zones.json`). |
| Situation | From active 2-minute suspensions (and red cards, counted as 2 minutes): `equal`, `powerplay` (more players), `shorthanded`. Efficiency per situation = goals / shots. 7 against 6 (empty net) is tagged on events (`attributes.empty_net`). |
| Score timeline | Score after every goal by match clock. |
| Best run | Longest series of goals by one team without a goal of the other team (BRIEF "Tor-Läufe"). |
| Longest own drought | Longest match-clock period without an own goal, from throw-off or the previous own goal. |
| xG | Sum of expected goals over non-blocked shots **with the inputs known** (a position; 7 m always). Shots without a position (official report, overlay goals) have no xG (`expected_goal` returns None). `xg_shots` = shots with xG, `xg_goals` = goals among them, `xg_coverage` = xg_shots / shots (null without shots): show xG only with enough coverage, and set it against `xg_goals`, not all goals. v1 is a logistic prior (`xg.py`, version `prior-1`): distance to goal, angle, shot type; 7 m fixed at 0.75. **An estimate**, labelled so in the UI, refitted on own data later. |
| Player rows | Per player (roster id) or jersey number for opponents: goals, shots, misses, posts, saved, blocked, turnovers by type, suspensions, assists, 7 m, xG; goalkeeper saves via `attributes.goalkeeper_id`. |
| Goalkeepers | Per keeper (`attributes.goalkeeper_id`, else `goalkeeper_number`, else "unknown"): shots on target faced (goal + save), saves, save %, by goal zone, by shot zone, 7 m. **xG against** = sum of xG of those shots; **GSAx** (goals saved above expected) = xG against minus goals against, both over the shots with xG (`xg_coverage` = those / faced); null unless at least 70 % of the saves and 70 % of the goals have xG (positions come mostly with goals: overlay, tracking, matched report goals; over the goals alone xG is always below the goals and every keeper would look bad). Misses and posts are not on target and are left out. |
| Plus-minus | Needs on-court intervals (tracking identity); not yet computed. |

## Physical (from tracking, estimates)
Computed per track in `handball_vision.physical` and summed per player once a track is identified
(jersey reading or manual assignment). Only observed positions count (the tracker's predictions in
between are not measurements). Positions are resampled to 5 Hz; steps across gaps over 1 s or faster
than 10 m/s are dropped, found before smoothing (a track taking over a neighbour 2 m away is one
jump, smoothed it would read as three plausible sprint steps); then smoothed over 600 ms within the
pieces between such breaks.

| Metric | Definition |
|---|---|
| Distance | Sum of smoothed steps (m). |
| Speed bands | walk < 2 m/s (7.2 km/h), jog 2 to 4 m/s, run 4 to 5.5 m/s, sprint >= 5.5 m/s (19.8 km/h). High intensity distance = run + sprint. |
| Sprints | Runs of at least 1 s at sprint speed. |
| Top speed | Highest speed held over 1 s (five consecutive valid 200 ms steps). |
| Heatmap | Share of time per cell of a 10 x 5 grid over the 40 x 20 m court (match direction, not normalised per half). |

Shot zones and goal zones: `packages/court/spec/zones.json` (goal zones always from the **shooter's view**;
the UI can mirror to the goalkeeper's view).

## Defence systems (from tracking, estimates)
`handball_vision.formation`, every 2 s window per team: the defended goal is the one nearest the team's
goalkeeper track (else where most field players are). The defence counts as **set** when at least 5 field
players are within 12 m of that goal and at least 4 opponents are in that half. Depth of the six defenders
closest to the goal: more than 8 m = advanced, more than 10.5 m = deep. 0 advanced 6:0, 1 advanced 5:1,
2 advanced 4:2, 3 advanced with a deep one 3:2:1, otherwise 3:3, 4 or more deep "offensiv / Manndeckung".
Windows merge into segments (single outliers tolerated), segments under 4 s are dropped.

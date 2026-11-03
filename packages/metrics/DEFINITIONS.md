# Metric definitions (BRIEF 4.8)

All metrics are computed from events and possessions (`handball_metrics.compute_match_stats`) and never
stored as truth; caches carry the metrics version and are recomputed when events change. Positions are
normalised so the attacked goal is at x = 40 (`packages/court`).

| Metric | Definition |
|---|---|
| Shots | Shots with outcome goal, save, miss or post. **Blocked shots are excluded** and reported separately (`shots_blocked`). |
| Shooting % | goals / shots (as above). |
| Saves (team) | Opponent shots with outcome `save`. |
| Save % | saves / (saves + goals against). Misses and posts are not shots on target and are excluded; posts are reported separately. |
| Attack efficiency | goals / possessions. Shown only when possessions are known. |
| Turnover rate | turnovers / possessions. |
| Turnovers by type | bad_pass, catch_error, steps, double_dribble, offensive_foul, line_violation, passive_play, other. |
| 7 m | `seven_m_awarded` from events of that type; 7 m shots and goals from shots with `shot_type = penalty`. |
| Fast break goals | Goals with zone `fast_break` (shot within 6 s after gaining possession, `zones.json`). |
| Situation | From active 2-minute suspensions (and red cards, counted as 2 minutes): `equal`, `powerplay` (more players), `shorthanded`. Efficiency per situation = goals / shots. 7 against 6 (empty net) is tagged on events (`attributes.empty_net`). |
| Score timeline | Score after every goal by match clock. |
| Best run | Longest series of goals by one team without a goal of the other team (BRIEF "Tor-Läufe"). |
| Longest own drought | Longest match-clock period without an own goal, from throw-off or the previous own goal. |
| xG | Sum of expected goals over non-blocked shots. v1 is a logistic prior (`xg.py`, version `prior-1`): distance to goal, angle, shot type; 7 m fixed at 0.75. **An estimate**, labelled so in the UI, refitted on own data later. |
| Player rows | Per player (roster id) or jersey number for opponents: goals, shots, misses, posts, saved, blocked, turnovers by type, suspensions, assists, 7 m, xG; goalkeeper saves via `attributes.goalkeeper_id`. |
| Goalkeepers | Per keeper (`attributes.goalkeeper_id`, else `goalkeeper_number`, else "unknown"): shots on target faced (goal + save), saves, save %, by goal zone, by shot zone, 7 m. **xG against** = sum of xG of those shots; **GSAx** (goals saved above expected) = xG against minus goals against. Misses and posts are not on target and are left out. |
| Plus-minus | Needs on-court intervals (tracking identity); not yet computed. |

## Physical (from tracking, estimates)
Computed per track in `handball_vision.physical` and summed per player once a track is identified
(jersey reading or manual assignment). Positions are resampled to 5 Hz and smoothed over 600 ms; steps
across gaps over 1 s or faster than 10 m/s are dropped.

| Metric | Definition |
|---|---|
| Distance | Sum of smoothed steps (m). |
| Speed bands | walk < 2 m/s (7.2 km/h), jog 2 to 4 m/s, run 4 to 5.5 m/s, sprint >= 5.5 m/s (19.8 km/h). High intensity distance = run + sprint. |
| Sprints | Runs of at least 1 s at sprint speed. |
| Top speed | Highest speed held over two consecutive 200 ms steps. |
| Heatmap | Share of time per cell of a 10 x 5 grid over the 40 x 20 m court (match direction, not normalised per half). |

Shot zones and goal zones: `packages/court/spec/zones.json` (goal zones always from the **shooter's view**;
the UI can mirror to the goalkeeper's view).

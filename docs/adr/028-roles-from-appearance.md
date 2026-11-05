# 028. Referees and goalkeepers from appearance

- Status: accepted
- Date: 2026-11-04
- Implements BRIEF 7.2 stage 4 (team and role assignment); complements ADR 025

## Context
Roles came from two rules: the kit colours entered for a match (referee colour, team colours) and
the goal-area position rule (`events.assign_goalkeepers`: a long track that mostly stays within
6.5 m of a goal is that team's goalkeeper). On the real clips both go wrong in ways that distort the
statistics:

- Horgen vs Möhlin: the referees (yellow/black) stand at the goal line, so the position rule made
  them goalkeepers; people on the bench and a red/white player carried the colour label "referee".
- Leimental vs Arbon: the referees (turquoise) were counted as home players.

The torso colour medians separate badly in amateur halls (on Möhlin the referees' colour is 15 Lab
units from the home team's), so a stricter colour rule cannot fix it.

## Decision
1. `handball_vision.roles.RoleClassifier`: ResNet18 (ImageNet) fine-tuned on person crops with role
   boxes from five Roboflow handball sets (CC BY 4.0, list in `ml/roles/README.md`), ONNX,
   64 x 128 input, softmax over player, goalkeeper, referee. It runs in the decoding pass every
   `role_every` frames (default 30) like the appearance network; probabilities are stored with
   the observations.
2. Per track the probabilities are averaged (`track_roles`, at least 4 looks).
3. `apply_roles` after the colour, position and formation steps:
   - **referee** when the mean referee probability is at least 0.7 and the largest, the kit colour
     is not the same as a team's (gap of 8 Lab units, a weak brake only), and at most two referee
     tracks overlap in time (most certain first). This overrules the goal-line position rule;
   - **not a referee**: a colour-only referee with a referee probability below 0.15 goes back to
     the nearest team, or to goalkeeper when it looks like one and stays at a goal;
   - **goalkeeper** for short tracks the position rule cannot judge: looks like one (at least 0.6)
     and spends at least half its time within 9 m of a goal; the team is taken from the position
     rule's goalkeeper at the same goal nearest in time.
   Changed labels carry `label_source: "role"`, and each track keeps `role_p`.
4. The worker loads the model from `role_model` (default `/models/roles.onnx`) when it is
   installed; without it the old rules apply unchanged.

## Results (5-minute clips, crops checked by eye)
| Clip | Changes | Checked |
|---|---|---|
| Horgen vs Möhlin 2017 | 7 referee, 1 goalkeeper, 16 back to a team | 5 of 5 new referee tracks are the referees; the demoted "referees" are players and bench people |
| Leimental vs Arbon 2024 | 7 referee | 7 of 7 are the referees |

Per crop on a held-out Roboflow set (unseen halls): player 97 %, goalkeeper 67 %, referee 69 %
recall; the track average and the constraints carry the rest.

## Consequences
- Bench people (coaches, substitutes next to the court) have no class of their own; they now go to
  the nearest team instead of "referee". A fourth class or a tighter court filter would remove them.
- The model is our own (Roboflow data CC BY 4.0, attribution in `ml/roles/README.md`); it still has
  to be hosted for the worker images (it is not in the repository).

## Addendum 2026-11-05: bench, staff and spectators at the court edge
### Context
`detection.filter_on_court` keeps feet within 1.5 m of the lines. On the real clips that still
includes the bench row (seated feet are 0.4 to 1.2 m beyond the sideline), coaches standing at
the bench and spectators sitting right at the court edge. They were tracked as players: on
Horgen vs Möhlin 21 % of all tracked detections were bench people labelled home or away, the
bench gave a home player the number 12 (a substitute in a black warm-up shirt) and made the home
team look far from its own goal, so the position rule gave both goalkeepers to the wrong team.
The tracker also hands bench tracks to players who pass the bench and back, so whole tracks
cannot be judged at once.

### Decision
`handball_vision.bench` cuts *stretches* of tracks, from court positions:

1. off court: the median foot point over 8 s lies beyond a **sideline** by at least 0.15 m or
   25 image pixels across the line at that spot (on the far side calibration errors of 10 to
   20 px put wings standing on the line 0.5 to 1 m outside); goal lines never count
   (goalkeepers, goal-line referees);
2. still: 90 % of that window within 2 m of its median (referees and players keep moving);
3. at least 6 s; gaps in the observations do not break a stretch while the person stays at the
   same spot; a stretch takes in the neighbouring looks within 2 m (standing up moves the foot
   point just inside the margin).

`pipeline._finish` applies it right after stitching, before colours, roles, goalkeepers,
formations, numbers and appearance learn anything. Bench stretches leave the tracks; the pieces
before and after become tracks of their own (a piece with fewer than 5 looks, or off court and
not moving like a referee, goes with the bench). Every look moves with its point: colour samples
now carry their frame (`TeamAssigner.add_sample`), role samples too. Downstream steps
(possession, events, formations, physical metrics, chunks, summary) only see the remaining
points, so nothing downstream needed a new label. What was removed is listed in
`extra["bench"]` (count, whole tracks, pieces, per stretch the track, time span and position).

Not done, from the measurements:
- an image-space fallback (outer band, still, seated box): tracks only exist after a court
  calibration (the pipeline fails fast or asks for points otherwise), and on the calibrated clips
  such a whole-track rule found 12 of 19, 2 of 10 and 5 of 16 of the tracks the court rule cuts;
- a fourth appearance class: the remaining misses are few (below) and mostly coaches standing
  or walking at the bench; not worth a model yet.

### Results (5-minute clips, every tracked detection on one frame per 10 s checked by eye, plus
every removed stretch on a contact sheet)
| Clip | Removed detections | Precision | Recall | Players removed |
|---|---|---|---|---|
| Horgen vs Möhlin 2017 (bench near side) | 76 of 379 sampled | 98.7 % (75/76) | 91 % (75/82) | 1 look (tracker swap) |
| Leimental vs Arbon 2024 (spectators near side) | 25 of 319 sampled | 100 % (25/25) | 89 % (25/28) | 0 |
| Horgen vs Stäfa 2017 (spectators behind the railing) | 17 stretches | 16 bench, 1 unclear | not counted | 0 tracks |

The one player look is a single point where a bench track briefly jumped to a player; the misses
are coaches standing at the bench, short stays and spectators during a goal celebration.
Effect without vs with the filter: Möhlin 8258 detections (21 %) gone, 3 mixed tracks change to
the team they show most of the time, both goalkeeper tracks to the team that defends that goal
(checked on the defence line), the bench number home 12 disappears, the home team's observed time
drops from 2039 to 1422 s and its distance from 2105 to 1889 m; Leimental 2859 detections of
spectators labelled away, away time 1718 to 1426 s, no other label changes; Stäfa 1307 detections
(spectators labelled home and referee) and a number 16 read on a spectator track. Possession could
not be compared (the cached clips have no ball observations).

### Consequences
- A substitute who walks onto the court starts a new track at that moment; merging by number
  joins the pieces again when the number is read.
- A far-side bench in the middle of the court stays: the 25 px margin is several metres there,
  beyond the 1.5 m court filter; it is usually filtered out by that filter already (Leimental).
- A team time-out at the bench is cut like the bench; play resumes in new tracks.

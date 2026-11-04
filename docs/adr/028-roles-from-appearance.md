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

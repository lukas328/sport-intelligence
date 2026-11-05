# 027. Shirt numbers read once, players recognised by appearance

- Status: accepted (numbers), proposed (re-identification, licence open: Q-ML-5)
- Date: 2026-11-04
- Implements BRIEF 7.2 stage 6; builds on ADR 025

## Context
Per-player figures need identities. The tracker loses players in crowds and on camera pans: a
5-minute clip gives 120 to 200 track pieces for about 16 people. A shirt number is readable on
about one crop in ten (back to the camera, sharp, unoccluded), so reading it on every piece is
impossible; but it only has to be read once per player, after that the player is recognised.
Tesseract read none of the numbers on 720p footage.

## Decision
1. **Reading** (`numbers.py`): PP-OCRv4 detection and recognition (Apache-2.0, ONNX, from the
   pinned `rapidocr_onnxruntime` wheel; ml/models/ppocr-v4.md) on the upper body of players at least
   80 px tall, sharp, inside the frame, green channel, enlarged three times. Every 6th frame on CPU,
   every detection frame on the GPU image.
2. **Per track**: confident readings (0.8 or more) are voted; a number needs 70 % of them and at
   least three readings (two only when both are very sure and alone). Where a track reads one number
   for a while and then another, it is cut there (the tracker swapped two players). Fragments of one
   team with the same number that do not overlap in time become one player (goalkeeper and field
   labels included: the number is the better witness).
3. **Recognising** (`reid.py`): an appearance network gives one vector per player and second; the
   tracks with a well-read number (at least four readings) teach, per match and team, a projection
   (PCA + LDA) that separates today's players. Every track without a number goes to the nearest
   player when clearly nearer than the second, the player is not on court elsewhere at that time,
   and the distances before and after can be run. Unsure stays unknown.
4. **In the API**: own players (home kit) with a number are linked to the roster entry with that
   shirt number; manual assignments still win and survive re-runs.

## Results (NLB 2017 clip, 5 minutes)
| | numbered player time |
|---|---|
| numbers read every 15th frame | 12 % |
| read on every detection frame, vote, split and join | 22 % (1716 s) |
| plus recognition by appearance | 30 % (2375 s) |

Hidden-number test (12 numbered players, 15-second pieces): 65 % assigned, 70 to 75 % of those
right. The remaining error source is a wrong anchor: a junk track (referee and spectators) with a
misread number attracts others.

## Consequences
- Numbers and the vote ship now; re-identification ships when Q-ML-5 is answered (the code path is
  in place and skipped without a model).
- CPU cost: reading numbers adds about 0.5 x video length at every 6th frame; the appearance
  network about 2 x on CPU, a few percent on a GPU. The GPU image is the production path.
- Next: reject anchors whose own appearance is inconsistent (junk tracks), and use the numbers'
  vote across tracks to repair the tracker earlier (association with appearance during tracking).

## Addendum (2026-11-05): the team of a number, no guessed referee kit, players-only ReID
Measured on four SG Wädenswil/Horgen NLB stream segments (Emmen, Arbon, Gossau, Baden-Endingen,
5 min each, cached observations of the worker's CPU path) against the official match sheets.
The digits were mostly read right; the loss was the team: a track carried a white home player and
a black opponent in turn (the tracker swaps them in crowds), so the opponent's number counted for
the home team; bench, staff, referees and goalkeepers with a number taught ReID.

1. **Team of a number from the shirt it was read on** (`pipeline.split_by_reading_colour`,
   `teams.team_centres / side_of / colour_runs`). Every confident reading gets the team of the
   torso colour sampled on the same crop, against this match's two team colours (2-means over the
   field tracks' single looks, started at the teams' track medians: a dim hall shows white shirts
   grey, Emmen L 60 to 70). A field track with two or more readings on the other team's shirt is
   cut at its colour switches (single looks smoothed over 1 s, stretches under 1 s ignored), each
   piece taking the team of its colour; then every reading that still disagrees with its track's
   team is dropped. Goalkeeper and referee tracks are left alone. Without two clearly different
   team colours nothing changes.
2. **No guessed referee kit.** The API sent `#1a1a1a` for the referee in every job; the referees of
   all four games wore yellow or orange, and a black "referee" kit next to black opponents splits
   the opponents between two labels. The match now has an optional `kit_referee` (user choice,
   migration 0030); the job carries it only when it is set and at least delta E 25 from both field
   kits (`core.colors.analysis_kits`), else referees come from the role classifier and the
   colour clusters. `roles.apply_roles` keeps its colour gap: it is what stops dark-kit players
   from being taken for referees; a referee in a team's colour is therefore not relabelled, and
   step 3 keeps such a track out of ReID instead.
3. **Players-only ReID** (`reid.plays`, `reid.fragment_roles`). A fragment teaches or gets a number
   only when it is labelled a field player and the role classifier, averaged over its looks (for a
   numbered fragment the looks within 2 s of its readings), gives "player" at least 0.75.

| game | step | read numbers on the sheet (tracks, time) | incl. appearance | numbered player time read / +appearance | active players found home / away | with roster | ReID hidden-number test right / wrong / none |
|---|---|---|---|---|---|---|---|
| Emmen | before | 9/17 (70 %) | 14/23 (72 %) | 31 / 37 % | 4/12, 5/15 | 11/14 (93 %) | 31 / 12 / 7 |
| | 1 | 9/14 (79 %) | 17/22 (82 %) | 30 / 35 % | 4/12, 5/15 | 11/13 (94 %) | 29 / 5 / 17 |
| | 1+2 | 9/14 (80 %) | 23/30 (82 %) | 26 / 34 % | 4/12, 5/15 | 11/13 (98 %) | 32 / 3 / 14 |
| | 1+2+3 | 9/14 (80 %) | 18/23 (83 %) | 26 / 32 % | 4/12, 5/15 | 11/13 (98 %) | 26 / 0 / 23 |
| Arbon | before | 14/18 (80 %) | 20/28 (76 %) | 38 / 48 % | 8/13, 4/11 | 15/17 (95 %) | 55 / 11 / 8 |
| | 1 | 14/15 (99 %) | 30/35 (90 %) | 27 / 44 % | 8/13, 4/11 | 14/15 (99 %) | 51 / 7 / 9 |
| | 1+2 | 14/15 (99 %) | 29/35 (92 %) | 23 / 41 % | 8/13, 4/11 | 14/15 (99 %) | 38 / 8 / 11 |
| | 1+2+3 | 14/15 (99 %) | 29/35 (92 %) | 23 / 39 % | 8/13, 4/11 | 14/15 (99 %) | 34 / 8 / 15 |
| Gossau | before | 15/22 (81 %) | 31/49 (78 %) | 32 / 48 % | 8/12, 5/12 | 17/17 (100 %) | 38 / 15 / 23 |
| | 1 | 14/20 (92 %) | 35/58 (79 %) | 28 / 44 % | 8/12, 5/12 | 15/15 (100 %) | 45 / 14 / 18 |
| | 1+2 | 14/21 (87 %) | 40/58 (77 %) | 29 / 49 % | 8/12, 5/12 | 15/16 (97 %) | 42 / 13 / 25 |
| | 1+2+3 | 14/21 (87 %) | 31/42 (82 %) | 29 / 40 % | 8/12, 5/12 | 15/16 (97 %) | 29 / 9 / 42 |
| Baden-Endingen | before | 11/12 (95 %) | 19/23 (88 %) | 26 / 41 % | 6/11, 4/15 | 12/13 (96 %) | 9 / 4 / 10 |
| | 1 | 11/12 (95 %) | 18/22 (88 %) | 27 / 41 % | 6/11, 4/15 | 12/13 (96 %) | 8 / 4 / 12 |
| | 1+2 | 11/12 (97 %) | 13/19 (87 %) | 34 / 41 % | 6/11, 4/15 | 12/13 (98 %) | 17 / 8 / 5 |
| | 1+2+3 | 11/12 (97 %) | 13/19 (87 %) | 34 / 41 % | 6/11, 4/15 | 12/13 (98 %) | 12 / 5 / 13 |

"On the sheet" counts a track as right when its number is on its team's official list; the
percentage weights by track time. Hidden-number test: numbered tracks cut into 10 s pieces, each
piece in turn loses its number and readings and must be found again (pieces differ per step
because the numbered tracks do).

- Step 1 removes the black-shirt numbers from the home team: Arbon's wrong home numbers 7, 8, 28
  -> 28, Emmen's 5, 6, 14, 19 -> 5, 8. The numbered time drops (Arbon 38 -> 27 %) because time a
  numbered track spent on the other team's player no longer counts; correct numbered minutes
  stay about the same (Arbon 11.6 -> 10.1 read, 13.8 -> 14.9 with appearance; Emmen 6.8 -> 7.3).
  ReID wrong answers fall (Emmen 12 -> 5, Arbon 11 -> 7). Remaining wrong numbers are misread
  digits on the right shirt (Gossau 69, 93, 15 on white shirts), which the roster fixes.
- Step 2 is right in principle (no game had a black referee) but moves the numbers both ways:
  the tracker uses the per-detection colour label, so its tracks change (Arbon's #4 track
  breaks into pieces that fall below the 70 % vote); the share of player time also grows because
  short black tracks are no longer called referees.
- Step 3 trades recall for precision: hidden-number wrong answers 32 -> 22 over the four games,
  right ones 129 -> 101. Filtering only the anchors (not the candidates) kept 112 right but had 33
  wrong: the dirty anchors are mostly numbers that are not on the sheet anyway; the candidates
  (referee and staff stretches that look like a player) are where the filter helps.
- Still open: the tracker swaps players of different teams (step 1 repairs the numbered tracks
  only); recall of active players is unchanged (4 to 8 of 11 to 15 per team); the role threshold
  (0.75) and the colour-run length are set on these four games only; the web form has no field for
  the referee kit yet.

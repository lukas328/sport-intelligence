# Ball detector (research, not shipped)

Finding the ball across halls, cameras and ball colours. Nothing here ships yet; the scripts are the
reproducible trail of the experiments. **Models trained with non-commercial data (DeepSport, see
below) are research models and must not go into the product.**

## Approach
1. **Three frames as input** (t-G, t, t+G; TrackNet principle): a ball moves against the hall, a
   spot on the wall or a lamp does not. `train_ballnet3.py` (CPU) and `kaggle/train_gpu.py` (Kaggle
   GPU): ResNet18 layers 1 to 2 plus a decoder, stride-4 heatmap, CenterNet focal loss, first conv
   extended to 9 channels (centre = single-frame weights, neighbours start at zero).
2. **Path over time** (`packages/vision/handball_vision/balltrack.py`): peaks linked at physically
   possible speeds, fixed spots dropped, best chain of reachable tracklets.
3. **Who has the ball** (`ballpossession.py`): the path against the player boxes. 78 % of the
   labelled balls lie in a player's box (held, at the body), so a per-player holder classifier
   (`holder_crops.py`, `train_holder.py`) is the second track.
4. **Self-training**: the net's long, moving tracklets on the full games (`mine_tracklets.py`,
   local static test against the surroundings) are checked as whole tracklets
   (`review_tracklets.py`); one look labels 10 to 30 frames.

## Data
| Source | What | Licence | Use |
|---|---|---|---|
| TeamTrack handball_side (Kaggle `atomscott/teamtrack`) | one hall, fisheye panorama, ball in every frame | MIT | `extract_teamtrack_triplets.py` |
| Our full games (Drive) | 3-minute segments per game, random tiles as negatives | own | `collect_game.py` |
| Labelled frames (labelling page "Ball-Labeling Halle", `labelling/frames.html`) | 130 frames from 7 halls, 80 with ball; per hall split in train and test half | own | `tiles_from_frames.py`, benchmark `bench_labelled.py` |
| Labelled paths (labelling page "Ball-Pfade Halle", `labelling/paths.html`) | 3-second scenes, a click every ~0.1 s, frames between interpolated | own | `tiles_from_paths.py` |
| DeepSport basketball instants (Kaggle `deepsportradar/basketball-instants-dataset`) | 16 arenas, frame pairs 40 ms apart, 3D ball centre with calibration | **CC BY-NC-SA 4.0** | research only: `deepsport_tiles.py` projects the ball, scales to 8 to 24 px |

Roboflow handball sets with ball boxes (CC BY 4.0, via API): handball-ballon v13, handball-xutbx v16, handball-detection-fj8rc v2, custom_handball_dataset v5, handball5 v1, about 2,900 balls (`roboflow_tiles.py`, still frames); handball-detection-2 checked and left out (mostly football photos).
Checked and not used:
basketball tracking (CC BY-NC-ND), sports-ball image classification (close-ups).

## Benchmark: labelled test half (40 balls, never trained on)
| Model | Top peak on the ball | Ball among top 5 peaks |
|---|---|---|
| Single-frame net (TeamTrack + 37 own) | 6 % (all 80) | 14 % (all 80) |
| 3-frame net, round 1 (TeamTrack) | 12 % | 23 % |
| round 2 (+ user frames, train half; Kaggle GPU) | 20 % | 28 % |
| round 3 (+ user ball paths, DeepSport basketball) | 33 % | 47 % |
| round 4 (+ Roboflow still frames) | 23 % | 45 % |
| round 6 (+ OWLv2 pseudo-labels from 189 segments, no training tiles within 2 s of a test frame; not promoted) | 33 % | 42 % |

Round 6 (2026-11-09, `kaggle/train_r6.py`, kept as `ball_r6.pt` in `handball-ball-models`) ties round 3 on the 40 test balls. It is more confident on the ball (score at least 0.3 on 45 % of the balls vs 23 %) but also on frames without a ball (median top peak 0.4 to 0.6 vs about 0.2). Round 3's 33 % is inflated by about 90 training tiles near test frames, round 6's is not. The test set is too small to separate the two (one ball is 2.5 points): grow it to about 200 balls before more GPU time goes into ball training.

## Benchmark: test set 2 (177 balls, 42 new halls, 2026-11-09)
252 frames from 42 games in halls never used for training or the first test (`testset_pick.py`,
games in `test_games.json`: leave them out of every ball training), 2-second clips, labelled on the
page "Ball-Testset: neue Hallen" (`labelling/testset.html`): 177 balls, 72 frames without a ball,
3 unsure. Half of the frames come from moments with a running match clock. `bench_testset2.py`
(CPU, about 10 minutes):

| Model | Top peak on the ball | Ball among top 5 | Score at the ball >= 0.3 | No-ball frames with a peak >= 0.5 |
|---|---|---|---|---|
| OWLv2 (suggestions, centre frame) | 44 % | 66 % | 51 % | 10 % |
| round 3 (`ball_best.pt`) | 15 % | 29 % | 11 % | 8 % |
| round 6 (`ball_r6.pt`) | 29 % | 51 % | 44 % | 43 % |
| round 7 (`ball_r7.pt`, 2026-11-10) | 35 % | 53 % | 50 % | 54 % |
| round 8 (`ball_r8.pt`, 2026-11-12) | 33 % | 50 % | 41 % | 44 % |

- With 177 balls one ball is 0.6 points (standard error about 3.5 points): round 6 is clearly better
  than round 3 in new halls. The first test (40 balls, 7 halls also in training) showed a tie: it
  mostly measured the known halls. The OWLv2 pseudo-labels help generalisation.
- Round 7 (`kaggle/train_r7_push.py`: round 6 plus OWLv2 labels from 144 more segments of 72 games,
  test set 2 halls held out, twice the negatives, motion blur, 30 000 steps from round 6; kept as
  `ball_r7.pt` in `handball-ball-models`): 35 % against 29 % top peak, the balls it gains outnumber
  the ones it loses 15 to 5 (paired, p = 0.04). But false alarms got worse (54 % of the frames
  without a ball have a peak of 0.5 or more), so more negative tiles of the same kind do not fix
  them. Next step there: find out what the false peaks sit on (body parts, ball racks, logos) before
  more GPU time.
- Round 6's weakness is false alarms: 43 % of the frames without a ball have a peak of 0.5 or more.
- The labeller saw OWLv2's suggestions (85 balls clicked on a suggestion), so OWLv2's numbers are
  optimistic where the ball is ambiguous; the nets did not see anything.
- Notes from labelling: many balls are covered by a body; balls in hands are found best; fast
  passes and shots are often blurred or invisible in a single frame; breaks bring warm-up balls.

### What the false peaks sit on (rounds 6 and 7, 2026-11-10)
Round 7 (`ball_r7.pt`) puts its top peak on the ball in 35 % but has a peak >= 0.5 on 54 % of the
72 no-ball frames. `false_alarms.py` (CPU, three stages: net peaks, pose, report) takes every peak
>= 0.4 of the top 5 that is not within 12 px of a labelled ball and sorts it by the nearest keypoint
of an RTMPose person (`rtmlib`, Apache-2.0, ONNX, YOLOX person detector, "balanced" mode) within
max(10 px, 0.1 x person height): head, hand (wrist), foot (ankle); else "body" inside a person box,
else "off-body". "Static" = local motion against its own surroundings < 0.2 (as in the round 6
pseudo-label filter).

| Category | r6 share | r7 share | r7 clock running | r7 clock stopped | r7 mean score | r7 static | true balls (same rule) |
|---|---|---|---|---|---|---|---|
| hand | 41 % | 41 % | 46 % | 37 % | 0.58 | 19 % | 43 % (76) |
| body | 19 % | 20 % | 23 % | 17 % | 0.56 | 19 % | 11 % (20) |
| off-body | 27 % | 25 % | 20 % | 30 % | 0.57 | 44 % | 34 % (61) |
| head | 9 % | 9 % | 7 % | 11 % | 0.55 | 21 % | 7 % (12) |
| foot | 4 % | 4 % | 3 % | 5 % | 0.52 | 0 % | 5 % (8) |
| false peaks | 347 | 362 | 187 | 175 | | 25 % | 177 balls |

- Top peaks >= 0.5 on the 39 no-ball frames of round 7: hand 19, body 9, off-body 9, head 1,
  foot 1. Ball frames where the top peak is a false one (94): hand 42, body 22, off-body 21, head 7.
- The false peaks sit where the balls sit: 45 % of the 177 true balls are within 15 px of a
  detected wrist (98 within 25 px), about as many as the false peaks (45 %). A hand filter from
  the pose model would remove half of the hits. 12 % of the true balls are "static" by the 0.2
  test (14 of them static and off-body), so a static filter (removes 25 % of the false peaks) or
  static and off-body (11 %) costs balls too: the ratio is poor.
- Check by eye (contact sheet of 40 round 7 crops, 8 per category): the location category was
  right in about 35 of 40. Errors: people the detector misses (bench, small far players) become
  "off-body"; a peak on the floor next to a shoe becomes "body". Many "foot" peaks are white
  shoes, some look like real balls (on the floor at the feet, a ball held over the head, a ball
  rack): perhaps 3 to 5 of 40 are real balls that are not the labelled game ball. Off-body
  peaks: logos, lamp reflections, railings, the ball rack. The human OWL tags (`owl_fp`) overlap
  our peaks only twice (both "hand", both auto "hand"): no real validation.
- Uncertainty: 72 no-ball frames and 42 halls; one frame is worth 1.4 points of the no-ball rate.
  Keypoint thresholds are set by hand, not tuned.

Next step (proposal): the pose model cannot tell an empty hand from a hand with a ball, and the
motion test cannot either (balls are held still too). The confusion is in appearance, so attack
hands first with a verifier crop classifier (ball / no ball, about 64 px around the peak, three
frames), trained with hard negatives cut automatically at wrists, heads and torsos of RTMPose
people where the frame has no labelled or OWL-confirmed ball near them, plus the static off-body
spots (logos, lamps, ball racks) from the round 6 hard-negative cells. As a cheaper first try,
the same negatives can go into the heatmap training of the next round. Hands and bodies are 61 %
of the false peaks and 64 of the 94 wrong top peaks on ball frames.

**Open-vocabulary detector, 24 balls of the test half (2 to 4 per hall):** OWLv2 base
(Apache-2.0, queries "a photo of a handball", "a ball", "a small ball in the air", 480 px tiles
upscaled to 960) puts its top box on the ball in 50 % (round 3 net on the same frames: 29 %,
top 5: 46 % vs 50 %). Its confident boxes are reliable: 10 of 11 boxes scoring at least 0.5 are
the ball. Too slow for the worker (about 2 min per frame on CPU), but a good teacher: its
confident boxes, kept only where the temporal path confirms them, become training labels for the
3-frame net (`kaggle/owl_gpu.py`, `owl_bench_local.py`).

On TeamTrack's own validation the 3-frame net finds 64 % at 2 % false alarms: the gap is the domain
(one hall vs many), not the method.

## Verifier on the top-5 peaks (test set 2, 2026-11-10)
A small crop classifier (ball / no ball) re-scores round 7's top-5 peaks per frame. Scripts in
`verifier/` (CPU only, paths as arguments): `data.py` (net peaks on the training tiles, RTMPose
people, crops), `train.py`, `eval.py`. Weights stay outside the repo.

- Data: the round 7 OWL tiles (test set 2 halls already excluded), 72 px crops, three frames
  stacked (9 channels). Positives: the confirmed ball (9 311) and round 7 peaks within 12 px of it
  (9 299). Negatives: round 7 peaks (score >= 0.05) more than 20 px from the ball (13 948), RTMPose
  wrists (9 013), noses (6 446) and torso centres (5 564) with no ball within 20 px (pose on 4 000
  of the 12 321 tiles: all no-ball tiles, then positives), the fixed ball-like spot of each no-ball
  tile (1 405), one random point per tile (10 716). 14 of 111 games held out whole for validation.
- Model: 4-stage conv net (145 k parameters, 64 px input), balanced batches (half positives),
  shift, flip, time reversal, brightness/contrast/colour mixing, motion blur, noise; 6 459 steps of
  128, 43 minutes on 4 CPU cores. Held-out games: AUC 0.91 against net peaks, 0.98 against hands.
- Test set 2 (re-ranking only, so "ball among top 5" stays 52.5 % for every scorer; "found at
  FA x" = top peak on the ball and above the threshold at which x of the 72 no-ball frames alarm,
  because the scores live on different scales and "no-ball >= 0.5" alone is not comparable;
  "score at the ball" = best of the five peaks within 12 px, where `bench_testset2.py` reads the
  heatmap near the label, hence 47.5 % instead of 50 % for the net):

| Scorer | Top peak on the ball | Score at the ball >= 0.3 | No-ball >= 0.5 | Found at FA 10 % | Found at FA 25 % | Top 1 vs net (gained / lost, McNemar p) |
|---|---|---|---|---|---|---|
| net alone (round 7) | 35.0 % | 47.5 % | 54 % | 15.8 % | 25.4 % | |
| verifier alone | 31.6 % | 44.6 % | 71 % | 15.3 % | 21.5 % | +9 / -15, p = 0.31 |
| net x verifier | 36.2 % | 37.9 % | 26 % | 18.1 % | 28.2 % | +8 / -6, p = 0.79 |
| sqrt(net x verifier) | 36.2 % | 46.3 % | 51 % | 18.1 % | 28.2 % | +8 / -6, p = 0.79 |

- Result: no measurable gain. The product moves 2 balls in top 1 (+1.2 points, p = 0.79) and finds
  4 more balls at the same false-alarm rate (10 %); both are within the noise of 177 balls (one
  ball = 0.6 points). The lower "no-ball >= 0.5" of the product (26 %) is only a change of scale:
  at matched false alarms it is almost the same as the net. The combination was fixed before the
  test run (no tuning on test set 2; there is no other honest tuning set, see below).
- Why: on the confident false peaks (>= 0.4) the verifier does separate better than the net
  (AUC against the 93 hit peaks 0.73 vs 0.61; body 0.78, head 0.75, off-body 0.74, hand 0.70), and
  the two scores are only weakly correlated (0.21). But it also rejects 22 % of the true balls
  (probability < 0.5; 16 % of the balls at a hand, 40 % of the balls on a body), and over all
  peaks, low ones included, it is weaker than the net (AUC 0.81 vs 0.83). Hands stay the hardest
  case: false hand peaks have a median probability of 0.62.
- Main limit of the data: round 7 was trained on these tiles and is almost perfect on them (top 1
  99 %, a no-ball tile with a peak >= 0.5 in 0.3 %), so its "hard" negatives on the training tiles
  are low-score peaks, not the confident mistakes it makes in new halls. The held-out games come
  from the same sources, so validation AUC (0.91) overstates what transfers (0.81 on test peaks).
- Next: hard negatives from halls the net has not seen (run round 7 on unlabelled frames of new
  games and keep confident peaks that OWLv2 and the temporal path do not confirm), more context
  for hands (96 px or the forearm direction), and cross-fitting (verifier trained on a net that did
  not see those tiles). A tuning set separate from test set 2 is needed before choosing how to
  combine the scores.

## Verifier v2 with human-labelled hard peaks (test set 2, 2026-11-12)
Scripts in `verifier/`: `v2.py` (crop format, human crops, game split), `train_v2.py`,
`tune_v2.py` (choice on the tuning set), `eval_v2.py` (test set 2, run once). Weights outside the repo.

- New data: 498 confident round 7 peaks (score >= 0.4, top 3 per frame) from 250 frames of 34 games,
  segments not in round 7's training, test set 2 halls excluded; labelled by hand: 135 ball, 363 no
  ball (2 unsure, dropped). Note: all 34 games also give OWL tiles (other segments) to round 7 and
  to the v1 crops, so these are new segments, not new halls.
- Split by game (seeded search for 1/3 of games with 1/3 of balls and of "no ball"): train 23 games
  (90 ball, 242 no ball), tuning 11 games (45 ball, 121 no ball). Test set 2 was used for nothing
  but the single final run.
- One crop format: the human crops were cut as 96 px per frame at 1280 wide (black outside), 2x
  bicubic, three frames side by side, JPEG 85. `v2.canon_frames` repeats that for the test set 2
  triplets, then the verifier's preprocessing (area down to 96 px, centre 64); the v1 crops go
  through the same 2x / JPEG / down round trip.
- Candidates (fixed before looking at the tuning set): v1; fine-tune of v1 (lr 5e-4, 1 211 steps of
  128, 6 min, batches 40 % human "no ball", 25 % human ball, 35 % v1 kinds); from scratch (5 060
  steps, 25 min, 25 % human "no ball", 15 % human ball, 60 % v1 kinds); each at half and at the end
  of training. Rules: net, verifier, s x v, s^0.25 v^0.75, s^0.75 v^0.25, a gate (v below the value
  that keeps 90 % of the tuning balls: score x 0.1). Highest tuning AUC wins.
- Tuning set (166 confident peaks; AUC with game-bootstrap 95 % interval; precision at 80 % / 90 %
  recall of the balls):

| Scorer | AUC | P@R80 | P@R90 |
|---|---|---|---|
| net alone | 0.670 [0.59, 0.75] | 0.34 | 0.29 |
| v1, verifier alone | 0.762 | 0.41 | 0.38 |
| v1, s^0.25 v^0.75 | 0.782 | 0.39 | 0.37 |
| from scratch, s^0.25 v^0.75 | 0.759 | 0.38 | 0.35 |
| fine-tune, verifier alone | 0.806 | 0.46 | 0.46 |
| fine-tune, s x v | 0.811 | 0.51 | 0.48 |
| **fine-tune, s^0.25 v^0.75 (chosen)** | **0.812 [0.73, 0.87]** | 0.46 | 0.46 |

  Gain of the choice over the net on the tuning set: +0.14 AUC (95 % interval +0.07 to +0.21).
  Even v1 already beats the net on confident peaks there; from scratch is worse than fine-tuning.
- Learning curve (fine-tune, same 1 211 steps, share of the human train crops kept per game; one
  seed each, so differences of 0.02 are noise):

| Human train crops | Verifier alone AUC | s^0.25 v^0.75 AUC | P@R80 | P@R90 |
|---|---|---|---|---|
| 0 % (v1 crops only: control for format and extra steps) | 0.784 | 0.797 | 0.45 | 0.39 |
| 25 % (17 ball / 66 no ball) | 0.758 | 0.773 | 0.41 | 0.39 |
| 50 % (42 / 123) | 0.790 | 0.796 | 0.41 | 0.42 |
| 100 % (90 / 242) | 0.806 | 0.812 | 0.46 | 0.46 |

  Most of the step from v1 (0.762) comes from the fine-tune itself on the unified format (0.784
  without any human crop); the 332 human crops add about +0.02 AUC and +0.07 precision at 90 %
  recall, within the noise of 45 tuning balls. The curve rises from 25 % to 100 % but is not
  conclusive.
- Test set 2, one run with the frozen choice (same definitions as the v1 table):

| Scorer | Top peak on the ball | Ball among top 5 | Score at the ball >= 0.3 | No-ball >= 0.5 | Found at FA 10 % | Found at FA 25 % | Top 1 vs net (gained / lost, McNemar p) |
|---|---|---|---|---|---|---|---|
| net alone (round 7) | 35.0 % | 52.5 % | 47.5 % | 54 % | 15.8 % | 25.4 % | |
| v2 fine-tune, s^0.25 v^0.75 | 35.6 % | 52.5 % | 40.1 % | 62 % | 18.6 % | 27.7 % | +11 / -10, p = 1.00 |

  Clock running (103 balls): top 1 39.8 % vs 37.9 %, FA 10 % 13.6 % vs 17.5 %; clock stopped (74):
  top 1 29.7 % vs 31.1 %, FA 10 % 17.6 % vs 10.8 %.
- Result: still no measurable gain on test set 2. Top 1 +0.6 points (+11 / -10), 5 more balls at
  10 % false alarms (+2.8 points) and 4 more at 25 %, all within the noise of 177 balls; "no-ball >=
  0.5" is worse only by scale (the rule pushes scores up). On the peak level the transfer is real
  but small: among confident test peaks (>= 0.4; 73 hits, 358 false) AUC net 0.771, verifier 0.807,
  rule 0.813 (v1: verifier 0.73 against the net 0.61 on its slightly different subset). Over all
  top-5 peaks the verifier stays below the net (0.801 vs 0.832), and frame-level top 1 depends on
  ranking the hit above the other four peaks of the same frame, many of them low and easy for the
  net. On test set 2 the net itself separates confident peaks better (0.77) than on the tuning
  games (0.67), so the tuning gain (+0.14) overstated what was left to win there.
- Next: more labels only with a better design: label confident peaks from new halls (not only new
  segments) and, per frame, all top-5 peaks, so the verifier learns the within-frame ranking that
  top 1 needs; then repeat the curve with 2 to 3 seeds per point. A second batch of 500 should go
  into training with the tuning games kept; enlarge the tuning set to about 100 balls before
  trusting a choice. Beyond that the remaining frame-level misses are mostly the 47.5 % of balls
  not among the top 5 at all, which no re-scorer can fix.

## Round 8: the owner's 1000 labelled peaks in training (2026-11-12)
`kaggle/train_r8_push.py`: round 7 plus the two "Ball oder nicht?" rounds (273 balls, 720 no ball,
from segments round 7 never saw) as 224 px native triplet tiles (986 tiles: 298 with a ball, 688
hard negatives), every third game held out as the validation group "human", 30 000 steps from
round 7 (3.7 h of training on Kaggle). Kept as `ball_r8.pt` in `handball-ball-models`.

| Test set 2 (177 balls, 72 frames without) | round 7 | round 8 |
|---|---|---|
| Top peak on the ball | 35 % | 33 % |
| Ball among top 5 | 53 % | 50 % |
| No-ball frames with a peak >= 0.5 | 54 % | 44 % |
| Top-1 hits at 10 % false alarms (threshold 0.83 / 0.78) | 16 % | 17 % |
| Top-1 hits at 25 % false alarms (threshold 0.67 / 0.64) | 25 % | 25 % |

- Paired on top 1: round 7 alone 12 balls, round 8 alone 8 (exact p = 0.50). **No measurable
  gain.** At the same false-alarm rate both nets find the same share of balls; round 8 mostly gives
  lower scores everywhere (fewer peaks >= 0.5, also at the ball: 41 % against 50 % with >= 0.3).
- Held-out human games (tile level): at 0.5 the share of labelled false peaks still firing drops
  from 38 % to 28 % while found balls drop from 75 % to 70 %; at 0.3 false peaks 67 % to 47 % with
  balls unchanged (81 %). So the net learned those mistakes, but it does not carry over to frame
  level in new halls.
- Reading: the main loss on test set 2 is recall, not false alarms: about half of the balls are not
  among the top 5 peaks at all. Labels of the net's own confident peaks (mostly held balls) cannot
  fix that. Next labelling round (round 3, `labelling/build_crops.py`, `hardneg_pick.py
  --clock-only`): moments of play only, half unsure peaks (0.2 to 0.5), moving peaks first, and a
  click on the true ball when the ring misses it (state "elsewhere"), which gives the missed balls
  as positives. In parallel: test set 2 at native resolution (ml/gpu/JOBS.md job 11).

## Findings
- Most earlier "ball" labels from Möhlin were a fixed, ball-like spot on the wall; the three-frame
  view shows it never moves. They taught the single-frame net the static-spot error.
- Zooming broadcast cameras break a translation-only camera compensation; the local static test
  (spot vs its own surroundings over three frames) separates balls (median 0.5) from fixed things
  (median 0.08).
- Amateur halls (Uznach) give far more usable ball candidates than league broadcasts.

## GPU (Kaggle)
- `kaggle/train_gpu.py`: first GPU trainer (CPU augmentation; data-bound at about 0.7 s per step).
- `kaggle/train_gpu_fast.py`: workers only decode (single-threaded); zoom, crop, flip, time reversal,
  hue rotation, saturation, gain and the target heatmap run on the GPU (`affine_grid`/`grid_sample`),
  mixed precision; starts from the best model in the `handball-ball-models` dataset. `CHECK_AUG=1`
  writes crops around the targets to check the augmentation by eye.
- `kaggle/mine_gpu.py`: self-training over the game segments (`handball-game-segments`): every frame
  through the net, peaks linked with balltrack, fixed and background-glued spots dropped, tracklet
  tiles saved for review.
Kaggle allows two GPU jobs at a time; a small queue script pushes the next kernel when a slot frees.

## Round 9: Claude's training clip labels (2026-11-14)
`kaggle/train_r9_push.py` over round 8: the owner's 1000 peaks plus 834 ball points Claude placed in
46 training clips without the owner's rough track (`ml/gold/export_train.py`, tiers sure / track;
on 8 pilot gold clips 98 % of such points lay within 12 px) and 741 hard negatives (the net's
strongest peak >= 0.3 at least 40 px from the labelled ball, `ml/gold/train_labels_r9.py`).
Started from round 8. Measured on the gold standard (42 clips, 1555 points, 12 px; OWLv2 boxes
taken from the round-8 gold run so only the net differs; `ml/gold/eval_ball.py`):

| Gold v1 | round 8 | round 9 | only r9 / only r8 hits | sign test p |
|---|---|---|---|---|
| Net top peak on the ball | 49.7 % | 51.5 % | 124 / 96 | 0.07 |
| Ball among the net's top 5 | 77.2 % | 78.5 % | 83 / 62 | 0.10 |
| Tracker v2 (net + OWLv2) | 69.0 % | 71.3 % | 70 / 35 | 0.001 |
| Product ball path (balltrack) | 32.1 % | 35.8 % | | |

- The first gain since round 7, small on the net alone and clear through the tracker (its
  parameters were tuned on round-8 output, so the round-9 number is if anything conservative).
  Points within a clip are not independent, so the p values are optimistic.
- Next: more clips and the owner's ball-or-not review of the unconfirmed (fast) points, then
  round 10; re-tune the tracker on round-9 output.

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

**Open-vocabulary detector, 24 balls of the test half (2 to 4 per hall):** OWLv2 base
(Apache-2.0, queries "a photo of a handball", "a ball", "a small ball in the air", 480 px tiles
upscaled to 960) puts its top box on the ball in 50 % (round 3 net on the same frames: 29 %,
top 5: 46 % vs 50 %). Its confident boxes are reliable: 10 of 11 boxes scoring at least 0.5 are
the ball. Too slow for the worker (about 2 min per frame on CPU), but a good teacher: its
confident boxes, kept only where the temporal path confirms them, become training labels for the
3-frame net (`kaggle/owl_gpu.py`, `owl_bench_local.py`).

On TeamTrack's own validation the 3-frame net finds 64 % at 2 % false alarms: the gap is the domain
(one hall vs many), not the method.

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

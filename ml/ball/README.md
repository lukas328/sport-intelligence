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

Checked and not used: Roboflow handball sets (site not reachable from the session; API needs a key),
basketball tracking (CC BY-NC-ND), sports-ball image classification (close-ups).

## Benchmark: labelled test half (40 balls, never trained on)
| Model | Top peak on the ball | Ball among top 5 peaks |
|---|---|---|
| Single-frame net (TeamTrack + 37 own) | 6 % (all 80) | 14 % (all 80) |
| 3-frame net, round 1 (TeamTrack) | 12 % | 23 % |

On TeamTrack's own validation the 3-frame net finds 64 % at 2 % false alarms: the gap is the domain
(one hall vs many), not the method.

## Findings
- Most earlier "ball" labels from Möhlin were a fixed, ball-like spot on the wall; the three-frame
  view shows it never moves. They taught the single-frame net the static-spot error.
- Zooming broadcast cameras break a translation-only camera compensation; the local static test
  (spot vs its own surroundings over three frames) separates balls (median 0.5) from fixed things
  (median 0.08).
- Amateur halls (Uznach) give far more usable ball candidates than league broadcasts.

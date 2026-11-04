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

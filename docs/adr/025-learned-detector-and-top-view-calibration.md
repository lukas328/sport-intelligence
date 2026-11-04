# 025. Learned person detector, single observation pass, automatic calibration via a top view

- Status: accepted
- Date: 2026-11-04
- Updates ADR 012 (detector default), ADR 020 (calibration of moving cameras no longer needs
  clicked points in the common case)

## Context
On the three real clips (NLB men 2017 x2, SPL2 women 2024; panning club and broadcast cameras in
multi-sport halls) the classical pipeline (ADR 012, 020) found the camera motion but neither people
reliably nor the court: automatic calibration failed or returned a wrong court on all three. Pretrained
weights were unreachable when ADR 012 was written; GitHub release assets are reachable now.

## Decision
1. **Detector: YOLOX-S COCO (Apache-2.0 code and weights)** via ONNX Runtime
   (`YoloxDetector`, model card `ml/models/yolox-coco.md`), weights baked into the GPU worker image
   at build time from the pinned GitHub release with a SHA-256 check (never in git). People in the
   whole frame; `filter_on_court` keeps feet on the court with a plausible box height and drops boxes
   cut by the frame edge. Without the weights file the classical path still runs.
2. **One decoding pass** (`observe.observe`): camera motion on every frame, detection on every 3rd,
   floor-marking segments every 90th, a small Lab sample of each torso. Stored as
   `analysis/observations.npz` next to `motion.npz`: a re-run with clicked points skips decoding and
   detection (seconds instead of minutes).
3. **Automatic calibration via a metric top view** (`topview.py`, `observe.auto_calibrate`):
   floor orientation from the two orthogonal marking directions (segments of many frames, walls and
   people masked, focal length from the camera motion); scale from person heights (1.75 m); a top
   view drawn from the aligned segments only; court template search (lines, players on the court,
   nobody behind the goal lines, goalkeepers in the goal mouths; six weightings in one pass); the
   candidates are refined on the goal frames (projected 3D posts and crossbar must fall on striped red
   and white paint) and the best goal fit wins. Court coordinates are normalised (camera on the near
   side y < 0, goal x = 0 on the camera's left). Plausibility: camera 1.5 to 25 m above the floor and
   outside the court, at least half of the people on the court, a minimum goal fit; otherwise
   `needs_calibration` and the dialog as before.
4. **Pose calibration from clicks**: with a known focal length only the camera pose is fitted
   (`calibrate_pose`); four goal-post feet are enough, crossbar points (`height_m = 2`) help.
5. **Tracking for panning cameras**: a track outside the current view waits (up to 90 s) instead of
   ageing and is matched again with a wider gate when the player comes back; a confident team label
   never jumps to the other team; stitching compares shirts by hue (video washes colours out) and the
   kit match uses hue for coloured kits and lightness for white, black and grey ones.

6. **Teams by this match's colours**: the tracks' median torso colours are clustered (3 to 5
   clusters, the pair with most players that is clearly apart and balanced are the teams) and matched
   to the entered kits by order (lighter to lighter, hue to hue); hall lighting shifts absolute
   colours too much. **Goalkeepers by position** (most of the time within 6.5 m of a goal) and by the
   team that defends that goal in set attacks.
7. **What video gives without the ball**: possession phases with a summary per side
   (`GET /matches/{id}/possessions`), fast breaks (the team runs 18 m towards the other goal within
   4 s of winning the ball), physical load per team and per track; the analysis tab shows them when no
   events were recorded, with the way to goals and shots (courtside marks, match sheet).
8. **Fallback**: when the detector finds fewer than three people in the median frame, the classical
   path runs (unusual footage; the synthetic test video).
9. **GPU image** (`Dockerfile.cuda`, CUDA 12.6, ONNX Runtime GPU, detection on every frame).

## Consequences
- All three real clips calibrate automatically (court about 0.5 to 1.5 m accurate judged by the
  goal frames and lines; docs/perf/real-videos.md). People per frame on the court: 13 to 15.
- CPU cost for 5 minutes of video on 4 cores: about 9 to 10 minutes (detection 4.5 to 6, camera
  motion 2.3, calibration 0.8 to 1.5). On a GPU the detection drops to well under a minute.
- The ball is not found by a COCO model; ball and shot events stay with tagging and imports.
- Track identities still fragment when players leave the view for long or cross each other; player
  identity needs shirt numbers (OCR) or manual assignment (existing UI).
- Goal detection assumes striped goal frames (red and white in all three halls); other colours lower
  the goal fit and send the match to the confirmation dialog.

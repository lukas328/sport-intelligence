# 012. Vision pipeline baseline without trained models

- Status: accepted
- Date: 2026-11-02

## Context
Stages 2 to 5 (calibration, detection, tracking, team assignment) normally use learned models (keypoint
model, RT-DETR-class detector, ReID). In this environment no pretrained weights or handball datasets are
downloadable (Hugging Face, PyTorch, Kaggle, Zenodo, Roboflow blocked; only PyPI/npm/Docker Hub), and no
real match videos are available yet (Q-DATA-1). The brief forbids fake results.

## Decision
1. `packages/vision` implements every stage behind an interface, with **classical computer vision as the
   default**, always marked `source = "heuristic"` (UI shows "geschätzt"):
   - calibration: line mask on the median frame, Hough boundary hypotheses scored by how many court-line
     points they explain, ICP refinement, plausibility checks (fails loudly instead of returning garbage);
     manual 4+ point calibration as `user_correction`;
   - detection: background model with selective update, greedy blob decomposition into player-sized boxes,
     feet estimated from the head when legs blend into the floor; `OnnxDetector` runs any exported model
     (batched, CUDA EP when available) as soon as weights are registered;
   - tracking: Kalman filter on the court plane, ByteTrack-style two-stage association, soft team-label
     cost, offline tracklet stitching (the analysis runs after the match);
   - teams: torso colour vs. the kit colours entered for the match (priors, no clustering).
2. A **synthetic match generator** (perspective camera, court, 2 x 7 players with numbers, referees,
   ball, phases with side switches) provides exact ground truth for tests, the evaluation harness
   (`ml/eval/run.py`), the benchmark (`ml/eval/bench.py`) and demo data (`make seed`). Synthetic data is
   never presented as real analysis and is labelled Demo.
3. Stage outputs: Parquet (all points, versions in metadata) and 30 s binary chunks for the browser.

## Consequences
- Calibration and runtime meet the brief's targets on the synthetic set; detection recall, MOTA and team
  accuracy do not (see docs/perf/eval-m3.md). Real-world accuracy is unknown until real videos exist.
- Replacing a stage with a trained model is a configuration change; the evaluation harness measures it
  against the same golden set (BRIEF 10.4 regression rule).

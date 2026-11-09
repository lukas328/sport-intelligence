# yolox-s (COCO) — person and ball detector

| | |
|---|---|
| Interface | `Detector` (`handball_vision.detection.YoloxDetector`) |
| Architecture | YOLOX-S (anchor-free, decoupled head), 640 x 640 input, 9 M parameters |
| Weights | `yolox_s.onnx`, release 0.1.1rc0 of Megvii-BaseDetection/YOLOX on GitHub |
| SHA-256 | `c5c2d13e59ae883e6af3b45daea64af4833a4951c92d116ec270d9ddbe998063` |
| Licence | code and weights Apache-2.0 (ADR 003: allowed in production) |
| Training data | COCO 2017 (annotations CC BY 4.0); no handball data, no fine-tuning yet |
| Classes used | COCO 0 `person`, 32 `sports ball`; everything else is ignored |
| Runtime | ONNX Runtime; CPU about 90 ms per 1280 x 720 frame on 4 cores, run on every 3rd frame |

## Use in the pipeline
People are detected in the whole frame (players, referees, bench, spectators); `filter_on_court`
keeps those whose feet stand on the court (plus 1.5 m) with a box height that fits a standing
person there, and drops boxes cut off by the frame edge. The detections also feed the automatic
calibration (camera height from person sizes, players on the court, goalkeepers in the goal
mouths; ADR 025).

## Measured on the three real clips (golden set, 2026-11-03)
- About 13 to 15 people per frame on the court after filtering (two teams plus referees); recall on
  far players good at 720p (see `docs/perf/real-videos.md`), spectators and bench removed by the
  court filter.
- The ball is practically never found (small, blurred, COCO is not trained on handballs); ball and
  shot events stay with tagging and imports until a handball model exists (Q-ML-2).

## Known limitations
- No class for goalkeeper or referee: roles come from shirt colours (`teams.py`).
- Occlusions in crowded 6 m situations merge players into one box now and then.
- Not trained on handball: a fine-tuned model (TeamTrack, own matches with consent) is the next step.

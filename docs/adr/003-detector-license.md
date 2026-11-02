# 003. Detector licence: Apache-2.0 models for production, Ultralytics only for research

- Status: accepted (production default), Ultralytics Enterprise licence open (Q-ML-1)
- Date: 2026-11-02

## Context
BRIEF 7.2 stage 3 names YOLO (Ultralytics) with an ADR on AGPL vs. Enterprise, alternative RT-DETR
(Apache-2.0). Ultralytics code and weights are AGPL-3.0. Its network clause means running it in a
closed SaaS obliges us to publish the full service source, unless we buy an Enterprise licence.

## Decision
- **Production default: an Apache-2.0 DETR-family detector** (RT-DETR / RT-DETRv2, alternatives
  D-FINE, RF-DETR; licence of each checkpoint verified and recorded in the model card), fine-tuned on
  handball data with classes `player`, `goalkeeper`, `referee`, `ball`.
- Ultralytics YOLO may be used **only** for research and as a benchmark baseline outside the product
  images. It is never a dependency of `apps/*`. A CI check (from M3) fails if `ultralytics` appears in
  a production lockfile.
- All detectors implement the `Detector` interface; switching is configuration (BRIEF 6.5).
- Export to ONNX, run via ONNX Runtime (CUDA EP) or TensorRT in FP16 (BRIEF 6.3 point 3).
- Same rule for all other models: tracking (ByteTrack / BoT-SORT, MIT), pose (RTMPose via rtmlib,
  Apache-2.0), OCR (PARSeq, Apache-2.0). Licence of weights and training data recorded per
  `ModelVersion` (data lineage, BRIEF 10.1).

## Consequences
- Slightly more integration work than the Ultralytics all-in-one CLI.
- Training data licences still matter separately: several datasets are non-commercial (EIGD-H CC BY-NC-SA,
  Play-by-Play CC BY-NC). Production models must only be trained on commercially usable data.

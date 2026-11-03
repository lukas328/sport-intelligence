# 013. Track identity, physical load and camera sync without trained models

- Status: accepted
- Date: 2026-11-03

## Context
M5 asks for jersey OCR with roster assignment, audio sync of goal cams, a goal-zone model and a
goalkeeper module. No trained jersey/digit model and no real footage are available yet (ADR 003, ADR 012,
Q-ML-2, Q-DATA-1). Coaches still need identities to get per-player numbers from tracking today.

## Decision
- **Identity**: `JerseyReader` interface with an ONNX implementation (any digit classifier with 101 outputs,
  class 100 = unreadable). `assign_numbers` turns noisy readings into one number per track: greedy in order of
  summed confidence, numbers unique per team among tracks that overlap in time, fragments that never overlap
  may share a number. Until a model is configured, identities are **assigned by hand** in the video
  (`PUT /videos/{id}/tracks/{n}/identity`) and carried over to the matching track of a re-run (same team,
  > 80 % time overlap).
- **Physical load**: computed per track in the GPU worker (`handball_vision.physical`): 5 Hz resampling,
  600 ms smoothing, gap and jump rejection, four speed bands, sprints, top speed, 10 x 5 heatmap. Stored as
  JSON on the track, summed per player in the API. Labelled "geschätzt".
- **Camera sync**: ingest stores 10 minutes of 8 kHz mono audio; a `sync` job on the GPU queue correlates
  onset envelopes (FFT) and applies the offset only above confidence 0.35. A manual offset always wins and
  stops automatic re-sync. All times in the UI are main-video times; other cameras are shifted.
- **Goalkeeper module**: computed from events (no model needed): keeper credited via
  `attributes.goalkeeper_id` / `goalkeeper_number` (set in the tagger or from paper reports), save % by goal
  zone and shot zone, 7 m, xG against and GSAx.

## Consequences
- Everything works on the manual path now; a trained jersey reader only fills `number`/`identity_source=model`.
- Physical numbers from one camera are rough (foot point noise, occlusions); the smoothing keeps standing
  players from "running" (tested), but absolute distances need validation on real footage with a reference
  (LPS or GPS vests), see OPEN_QUESTIONS Q-ML-4.
- The goal-zone model (automatic goal zones from goal cams) is not built; goal zones come from tagging,
  feeds or paper reports.

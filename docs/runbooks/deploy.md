# Deploy and rollback

Who: on-call engineer. Pipeline: GitHub Actions `ci` must be green on `main` (lint, types, unit tests,
migrations check, image scans, compose stack with Playwright).

1. Tag the release `vYYYY.MM.DD-N`; images are built once and promoted (same digest to staging and
   production).
2. **Migrations first:** run the `migrate` image (`alembic upgrade head`) against the target database.
   Migrations are additive (new columns nullable or with server defaults), so the previous app version
   keeps working during the rollout.
3. Roll out API, workers, GPU worker and web (rolling update, readiness on `/readyz` and `/api/healthz`).
4. Verify: `/readyz` all `ok`, sign-in, open a match with video, `/internal/stats` queues draining,
   error rate and p95 in the dashboard for 15 minutes.

Rollback: redeploy the previous image digests. Do **not** downgrade the database; if a migration itself
is faulty, write a forward fix. Restoring data is a last resort (backup-restore.md).

## Video analysis worker (ADR 025)
- **Images**: `apps/gpu-worker/Dockerfile` (CPU, ONNX Runtime) and `apps/gpu-worker/Dockerfile.cuda`
  (CUDA 12.6 / cuDNN 9, `onnxruntime-gpu`; run with `--gpus all`). Both bake the YOLOX-S weights
  into `/models/yolox_s.onnx` from the pinned GitHub release and check the SHA-256 at build time.
  Without the file the worker runs the classical detector (ADR 012).
- **Settings** (`HB_` prefix): `DETECTOR_MODEL` (default `/models/yolox_s.onnx`), `DETECT_EVERY`
  (CPU image 3, CUDA image 1), `DETECTOR_THREADS` (0 = ONNX Runtime default).
- **Throughput**: CPU, 4 cores: about 2 x video length (5 min clip: 10 to 11 min; a 60 min match:
  about 2 h, within the 6 h job timeout). On a GPU the detection drops below real time; camera motion
  (about 0.45 x video length on CPU) then dominates.
- **Check after a deploy**: upload a short real clip, the analysis ends with `analysis_done` (or
  `analysis_needs_calibration` for an unusual hall) in the GPU worker log; the match page shows the
  possession share and attacks under Analyse.
- **Re-runs with clicked court points** reuse `analysis/observations.npz` and `analysis/motion.npz`
  and finish in seconds.
- **Abandoned uploads** (no progress for 3 days) are aborted by the hourly ops tick
  (`abandoned_uploads` in `/internal/ops/tick`).

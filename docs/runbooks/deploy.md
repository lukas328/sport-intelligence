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

# Handball AI Plattform (working title)

Upload a match video, everything else happens automatically: match report, clips, statistics, plays on a tactics board, and insights with video evidence.

> Status: milestones **M0 to M11** and addendum steps **A1 to A4** are built, as far as possible
> without real clubs, devices and provider accounts (reports per step in `docs/progress/`). What is
> still open before real clubs use it: `GO_LIVE.md`; later work: `docs/plans/backlog.md`. The full
> brief is in `docs/BRIEF.md` and `docs/BRIEF_ADDENDUM_01.md`, the plan in `docs/PLAN.md`.

## Quick start

Requirements: Docker, [uv](https://docs.astral.sh/uv/), Node 22 + pnpm 10.

```bash
make install     # uv sync + pnpm install + pre-commit hooks
docker compose up -d --build
open http://localhost:3000/status
```

| Service | URL |
|---|---|
| Web | http://localhost:3000 (status page: `/status`) |
| API | http://localhost:8000 (`/healthz`, `/readyz`, docs at `/v1/docs`) |
| S3 (SeaweedFS) | http://localhost:9000 |
| Mailpit | http://localhost:8025 |

## Everyday commands

```bash
make test              # Python (pytest, coverage gate 80 %) + Vitest; starts Postgres (make db),
                       # which the API tests need, everything else runs without services
make lint typecheck    # ruff, import contracts, eslint, madge, mypy strict, tsc strict
make test-integration  # against the running stack
make test-e2e          # Playwright + axe against http://localhost:3000
make help              # everything else
```

## Layout

```
apps/api              FastAPI (Python 3.12): REST API /v1, enqueues the worker jobs
apps/worker           RQ: video ingest and link import, exports, highlight reels, push, hourly tick
apps/gpu-worker       RQ: video analysis and camera sync (on CPU until a GPU provider is set up)
apps/web              Next.js 15 web app (PWA)
apps/mobile           Expo app for iOS and Android (scenes, dates, recording, courtside marks)
apps/site             Next.js marketing site and help centre (static)
packages/court        court geometry (JSON spec, generated for Python and TS)
packages/vision       computer vision: calibration, detection, tracking, teams, events
packages/jobkit       shared job helpers: progress reports to the API, storage, settings, URL check
packages/metrics      statistics and insights from events and tracks
packages/api-client   TS client generated from the OpenAPI schema
packages/client-core  logic shared by web and mobile (marks queue, deep links, upload plan)
packages/tactics      tactics board format and renderer
packages/ui           placeholder for shared UI components (empty)
packages/plans        plan catalogue for the site, generated from the API
ml/                   datasets, training, eval
infra/                compose, terraform
docs/                 brief, plan, ADRs, progress, runbooks
```

Behind a TLS-intercepting proxy, see `compose.override.example.yaml`.

Test videos and paper reports never go into git, see `data/README.md`.

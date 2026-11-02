# Handball AI Plattform (working title)

Upload a match video, everything else happens automatically: match report, clips, statistics, plays on a tactics board, and insights with video evidence.

> Status: **M0 Foundation**. See `docs/progress/M0.md`. The full brief is in `docs/BRIEF.md`, the plan in `docs/PLAN.md`.

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
make test              # Python (pytest, coverage gate 80 %) + Vitest, no services needed
make lint typecheck    # ruff, import contracts, eslint, madge, mypy strict, tsc strict
make test-integration  # against the running stack
make test-e2e          # Playwright + axe against http://localhost:3000
make help              # everything else
```

## Layout

```
apps/api          FastAPI (Python 3.12)          apps/web          Next.js 15
apps/worker       RQ, pipeline graph             apps/gpu-worker   GpuBackend (local, runpod, modal, k8s)
packages/court    court geometry (JSON → Py/TS)  packages/api-client  generated TS client
packages/metrics  metrics (M4)                   packages/tactics  tactics board format (M6)
ml/               datasets, training, eval       infra/            compose, terraform
docs/             brief, plan, ADRs, progress
```

Behind a TLS-intercepting proxy, see `compose.override.example.yaml`.

Test videos and paper reports never go into git, see `data/README.md`.

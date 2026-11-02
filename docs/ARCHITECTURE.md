# Architecture

Status: M0 (foundation). This document grows with each milestone.

## System overview

```
 Browser (Next.js 15, PWA)
   │  HTTPS, httpOnly session cookie, SSE
   ▼
 web (Next.js server)  ──server-side fetch──►  api (FastAPI, /v1)
                                                 │  SQLAlchemy 2 (async)     ┌──────────────┐
                                                 ├──────────────────────────►│ Postgres 16  │ RLS per org
                                                 │  enqueue                  └──────────────┘
                                                 ├──────────────► Redis (RQ queues: default, pipeline, gpu)
                                                 │  presigned URLs                 │
                                                 └──────────────► Object storage (S3)  ◄──┐
                                                                     videos, HLS,         │
                                                                     Parquet stage outputs│
                       worker (CPU, RQ) ── orchestrates PipelineGraph ─────────────────────┤
                       gpu-worker (RQ, GpuBackend: local | runpod | modal | k8s) ──────────┘
```

| Component | Path | Tech | Status |
|---|---|---|---|
| Web | `apps/web` | Next.js 15 App Router, TS strict, Tailwind 4, TanStack Query, next-intl (de-CH, en, fr) | M0: home, status page |
| API | `apps/api` | FastAPI, Pydantic v2, SQLAlchemy 2 async, Alembic, structlog, Sentry (opt-in) | M0: health, errors, DB base |
| Worker | `apps/worker` | RQ, pipeline graph | M0: graph + stage declaration, ping job |
| GPU worker | `apps/gpu-worker` | RQ, `GpuBackend` | M0: local backend, cost accounting |
| Court | `packages/court` | JSON spec → generated geometry for Python and TS | M0: lines, keypoints, normalisation |
| Metrics | `packages/metrics` | Python (+ TS types) | M4 |
| Tactics | `packages/tactics` | TS data format, renderer | M6 |
| API client | `packages/api-client` | openapi-typescript + openapi-fetch | M0: generated from `/v1/openapi.json` |
| UI | `packages/ui` | shared components | M1+ |
| ML | `ml/` | datasets, training, eval, model cards | M3+ |

## Principles (from BRIEF 6.5)
- **Ports and adapters**: storage, GPU, e-mail, payment, LLM, official feed and video import sit behind
  interfaces. Domain code knows no provider.
- **Pipeline as a graph** (`handball_worker.pipeline`): stages declare inputs/outputs; order, caching and
  partial reprocessing are derived. A user correction only reruns downstream stages
  (`PipelineGraph.downstream(["corrections"]) == ["metrics", "insights", "clips"]`).
- **Derived statistics are never truth**: computed from events/possessions/tracks into caches keyed by
  pipeline version.
- **Configuration over code**: thresholds, zones, plan limits, feature flags in versioned config.
- **Versioned public API** under `/v1`, OpenAPI is the contract, TS client generated from it.

## API conventions
- Errors: RFC 9457 `application/problem+json` everywhere (`handball_api.core.errors`), type URIs
  `urn:handball-platform:problem:<code>`. Unhandled errors never leak details.
- Every response carries `x-request-id` (propagated from the request if present) which is bound into
  every log line.
- Probes: `GET /healthz` (liveness), `GET /readyz` and `GET /v1/health` (readiness: Postgres, Redis, S3,
  each with latency, 503 when degraded).

## Module boundaries (checked in CI)
- Python (import-linter): apps are independent of each other; `handball_court` imports no app; API layers
  `main > routers > services > core`.
- TypeScript (madge): no circular imports in `apps/web/src` and `packages/*/src`.

## Local environment
`docker compose up` (root `compose.yaml` includes `infra/docker-compose.yml`): postgres, redis, s3
(SeaweedFS, ADR 006), mailpit, migrate (one-shot: alembic + bucket bootstrap), api, worker, gpu-worker
(CPU fallback), web. Ports: web 3000, api 8000, S3 9000, mailpit UI 8025.

## Data layout (planned)
- Postgres: tenants, users, rosters, matches, events, possessions, insights, billing, audit.
- Object storage: `videos/<org>/<match>/<asset>/` original, HLS, proxy; `artifacts/<org>/<match>/<stage>/<cache_key>.parquet`.
- Tracking frames are Parquet only, streamed to the browser in 30 s Arrow chunks.

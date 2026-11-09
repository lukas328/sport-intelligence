# Architecture

Status: M1 (accounts, tenants, roster). This document grows with each milestone.

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
                                                                     analysis outputs     │
                       worker (CPU, RQ: pipeline + default) ───────────────────────────────┤
                       gpu-worker (RQ: gpu, analysis on CPU until a GPU provider is set) ──┘
                         both report progress and results to api /internal/jobs/{id}
```

There is no orchestrator between the API and the workers: the API enqueues each job itself, by
function path only (it never imports worker code, ADR 001), and decides the next step when a job
reports back. One `processing_jobs` row per job holds status, progress, stages, result and the
GPU time used.

| Job (function path) | Queue | Enqueued by the API when |
|---|---|---|
| `handball_worker.ingest.run_ingest` | pipeline | an upload or link import finished: probe, quality check, HLS ladder, analysis proxy, poster, thumbnails |
| `handball_worker.ingest.run_import` | pipeline | a video link was submitted (SSRF check on every hop, `handball_jobkit.net`) |
| `handball_gpu_worker.analysis.run_analysis` | gpu | the ingest of the main video succeeded (plan allows tracking), or the coach marked the court |
| `handball_gpu_worker.sync.run_sync` | gpu | a second camera's ingest succeeded (audio offset to the main video) |
| `handball_worker.export.run_presentation_export` | default | a presentation is exported as video |
| `handball_worker.reels.run_highlight_reel` | default | a highlight reel is requested |
| `handball_worker.push.send` | default | an in-app notification goes to devices |

The worker also runs an hourly tick (RQ scheduler, `handball_worker.ticks`) that calls the API's
internal tick endpoint; the API decides what is due (preparation reports, dunning, official data
sync). `apps/api/tests/test_job_paths.py` checks that every function path exists and that the
payloads the API queues fit the parameters (and payload keys) of the worker functions.

| Component | Path | Tech | Role |
|---|---|---|---|
| Web | `apps/web` | Next.js 15 App Router, TS strict, Tailwind 4, TanStack Query, next-intl (de-CH, en, fr) | web app (PWA), proxies `/v1` to the API |
| Mobile | `apps/mobile` | Expo, expo-router, TS strict | native app: scenes, dates, recording, courtside marks, push (ADR 022) |
| Site | `apps/site` | Next.js 15, static | marketing site and help centre |
| API | `apps/api` | FastAPI, Pydantic v2, SQLAlchemy 2 async, Alembic, structlog, Sentry (opt-in) | REST API `/v1`, RLS tenancy, enqueues and follows the jobs |
| Worker | `apps/worker` | RQ, ffmpeg, Pillow | ingest, link import, exports, reels, push, hourly tick |
| GPU worker | `apps/gpu-worker` | RQ, `packages/vision` (OpenCV, ONNX Runtime) | video analysis, camera sync |
| Vision | `packages/vision` | Python, OpenCV, ONNX Runtime | calibration, detection, tracking, teams, numbers, events |
| Jobkit | `packages/jobkit` | Python | shared by the workers and the API: progress reporter, S3 helpers, job settings, SSRF URL check |
| Court | `packages/court` | JSON spec, generated geometry for Python and TS | lines, keypoints, normalisation |
| Metrics | `packages/metrics` | Python (+ TS types) | statistics and insights |
| Tactics | `packages/tactics` | TS data format, renderer | tactics board |
| API client | `packages/api-client` | openapi-typescript + openapi-fetch | generated from `/v1/openapi.json` |
| Client core | `packages/client-core` | TS | logic shared by web and mobile |
| UI | `packages/ui` | TS | placeholder for shared components (empty so far) |
| ML | `ml/` | datasets, training, eval, model cards | |

## Principles (from BRIEF 6.5)
- **Ports and adapters**: storage, GPU, e-mail, payment, LLM, official feed and video import sit behind
  interfaces. Domain code knows no provider.
- **Jobs chained by the API**: each video step is one RQ job; the API enqueues the next one when a
  job reports success (ingest, then analysis and camera sync). Corrections by users do not re-run
  jobs: statistics and insights are recomputed from the events. (`handball_worker.pipeline` with
  `PipelineGraph` is early scaffolding that nothing runs; see the backlog.)
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

## Identity, tenancy, permissions (M1)
- Data model: `users`, `auth_sessions`, `auth_tokens` are global. Tenant tables carry `organization_id`
  with `ON DELETE CASCADE` from `organizations`: `org_memberships`, `teams`, `seasons`, `memberships`,
  `players`, `roster_entries`, `invitations`, `consents`. `audit_logs` is append-only.
- Every member of a club has an `org_memberships` row (`org_admin` or `member`); team roles live in
  `memberships` (`coach`, `analyst`, `player`, `goalkeeper`, `guest`).
- URLs carry the tenant: `/v1/orgs/{org_id}/...`. The `org_scope` dependency resolves the caller's
  roles (404 if not a member) and sets `app.current_org` for the transaction.
- **Permissions**: one table in `services/policies.py` (rendered to `docs/policy-matrix.md`), enforced in
  the service layer; `tests/test_policy_matrix.py` runs every role against every endpoint.
- **RLS** (ADR 005): the API connects as `handball_app` (no superuser, no BYPASSRLS). Policies allow rows
  of `app_current_org()`; `org_memberships` and `organizations` are also visible for the current user's
  own memberships. Two audited system paths switch on `app.bypass_rls` for one transaction: organisation
  creation and invitation lookup by token.
- Auth details: ADR 008. E-mail: ADR 009.
- Web: the browser calls `/v1/*` on the web origin; a Next.js route handler proxies to the API. Server
  components call the API directly with the user's cookies (`serverApi()`).

## Module boundaries (checked in CI)
- Python (import-linter): apps are independent of each other; `handball_court` imports no app; API layers
  `main > routers > services > schemas > models > core`.
- TypeScript (madge): no circular imports in `apps/web/src` and `packages/*/src`.

## Local environment
`docker compose up` (root `compose.yaml` includes `infra/docker-compose.yml`): postgres, redis, s3
(SeaweedFS, ADR 006), mailpit, migrate (one-shot: alembic + bucket bootstrap), api, worker, gpu-worker
(CPU fallback), web. Ports: web 3000, api 8000, S3 9000, mailpit UI 8025.

## Data layout (planned)
- Postgres: tenants, users, rosters, matches, events, possessions, insights, billing, audit.
- Object storage: `videos/<org>/<match>/<asset>/` original, HLS, proxy; `artifacts/<org>/<match>/<stage>/<cache_key>.parquet`.
- Tracking frames are Parquet only, streamed to the browser in 30 s Arrow chunks.

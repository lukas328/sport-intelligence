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

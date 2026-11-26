# Monitoring and alerting (M9)

Signals and where they come from:

| Signal | Source | Alert when | Severity |
|---|---|---|---|
| Availability | external probe on `GET /healthz` (web and API) every 30 s | 3 failures in a row | page |
| Dependencies | `GET /readyz` (database, Redis, storage with latency) | any component `error` for 2 min | page |
| API latency | OpenTelemetry traces (`HB_OTEL_ENDPOINT`) → span metrics | read p95 > 300 ms for 10 min (BRIEF 7.3) | ticket |
| API errors | span metrics / logs (`status >= 500`) | 5xx rate > 1 % for 5 min | page |
| Job queues | `GET /internal/stats` (header `x-internal-token`) | `queues.gpu` > 20 or `oldest_queued_s` > 1800 | ticket |
| Failed jobs | `/internal/stats.failed_last_hour` | > 5 per hour | ticket |
| Stuck jobs | `/internal/stats.running_over_budget` (`running_over_3h` counts long jobs; a full game's analysis runs longer) | > 0 | ticket |
| Payments | Stripe dashboard + in-app admin notifications (`payment_failed`) | webhook delivery failures | ticket |
| Backups | nightly `infra/scripts/backup.sh` exit code, monthly restore test | missing or failed run | page |
| Certificates | probe on the public hostname | expiry < 14 days | ticket |
| Error tracking | Sentry (`HB_SENTRY_DSN`) | new issue in production | ticket |

Dashboards: requests per second and p95 per route, 5xx rate, queue depths, GPU minutes per day,
uploads per day, sign-ups, active clubs.

## Additions (addendum 01, 4.12)

`GET /internal/stats` now also returns `metrics` and `alerts`; the probe pages on any entry in
`alerts`.

| Alert key | Rule | Default threshold (setting) |
|---|---|---|
| `error_rate` | failed share of jobs finished in the last 24 h (at least 10 jobs) | > 10 % |
| `analysis_duration` | p95 of successful analyses in the last 7 days | > 45 min (`HB_ALERT_ANALYSIS_MINUTES`, P10) |
| `cost_per_match` | mean `cost_chf` of successful analyses in the last 7 days | > CHF 2 (`HB_ALERT_COST_CHF_PER_MATCH`, P10) |
| `ai_corrections` | correction rate of automatic events in the latest week vs. the 4 weeks before (min. 20 events per week) | > max(10 %, 1.5 x baseline) |
| `ai_confidence` | mean confidence of automatic events in the latest week | drop > 0.1 vs. baseline |

The backoffice shows the weekly AI quality table (`/v1/ops/quality`): automatic events, mean
confidence, share below 0.6 and correction rate per ISO week.

**Status page:** the hourly worker tick calls `/internal/ops/tick`, which runs the readiness checks
and posts the component states to the external status page (`HB_STATUS_PAGE_PUSH_URL`, bearer
`HB_STATUS_PAGE_TOKEN`; ADR 018). Database and storage down = "down", others = "degraded".

**Storage policy:** the same tick deletes original uploads after `HB_RAW_VIDEO_DAYS` (default 90)
once HLS and the analysis proxy exist; club admins get a notification 7 days before.

## Azure (since 2026-11-25, `infra/terraform/azure`, variable `monitoring`)

What the Azure environment alerts on today, by e-mail to `alert_emails` (action group
`ag-<prefix>-ops`). The probe runs only for the environment the app domain is bound to.

| Alert | Source | Fires when | Severity |
|---|---|---|---|
| `availability` | Application Insights standard test `GET https://<app_domain>/api/healthz` every 15 min from 2 locations (`probe_locations`), with the certificate check | all locations fail, or the certificate expires within 14 days | 1 |
| `api-errors` | Log Analytics, API console log lines `unhandled_exception` (every unexpected 500) | more than 3 in 15 min | 1 |
| `job-failures` | Log Analytics, API lines `job_failed` (each failed job) and `job_failed_silent` (watchdog) | 3 or more in 1 h | 2 |
| `out-of-memory` | Log Analytics, Container Apps system log `OOMKilled` | any in 15 min | 2 |
| `postgres-storage` | Postgres metric `storage_percent` | above 80 % (max over 1 h) | 2 |
| budgets | Cost Management (resource group, GPU job) | 80 % / 100 % forecast; GPU 20 and 30 | mail |

Not covered yet: queue depth and stuck jobs from `/internal/stats` (internal ingress, no outside probe;
the watchdog restarts silent jobs, `job-failures` sees the second failure), latency p95 (needs
OpenTelemetry), Sentry. Rough cost: the probe about 7 USD per month, the log alerts about 0.50 USD each.
A paused environment disables the probe and the log alerts.

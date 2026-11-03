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
| Stuck jobs | `/internal/stats.running_over_3h` | > 0 | ticket |
| Payments | Stripe dashboard + in-app admin notifications (`payment_failed`) | webhook delivery failures | ticket |
| Backups | nightly `infra/scripts/backup.sh` exit code, monthly restore test | missing or failed run | page |
| Certificates | probe on the public hostname | expiry < 14 days | ticket |
| Error tracking | Sentry (`HB_SENTRY_DSN`) | new issue in production | ticket |

Dashboards: requests per second and p95 per route, 5xx rate, queue depths, GPU minutes per day,
uploads per day, sign-ups, active clubs.

# Local stack without Docker images

Who: anyone working on the code, typically a cloud session. Use it when `make up` fails because
Docker Hub refuses image pulls (`429 Too Many Requests`) or no Docker daemon runs.

`scripts/local-stack.sh` runs the same services as `infra/docker-compose.yml`, from the host:

| Service | Here | In compose |
|---|---|---|
| Postgres 16 | `service postgresql` (roles `handball`, `handball_app` as in `infra/postgres/init`) | `postgres:16-alpine` |
| Redis | `service redis-server` | `redis:7-alpine` |
| S3 | moto server on port 9000 (`uvx moto[server]`), region `us-east-1` | SeaweedFS |
| E-mail | console backend (mails go to `api.log`) | Mailpit |
| API, worker, GPU worker | `uv run handball-api`, `handball-worker`, `handball-gpu-worker` | own images |
| Web | `next dev` (or `next start` after a build) on port 3000 | own image |

## Steps

```bash
make install                       # once: uv sync, pnpm install
HB_WEB_DEV=1 scripts/local-stack.sh up   # migrations, buckets, all processes; about 1 minute
make seed                          # demo club, matches, synthetic videos through the real pipeline
```

Sign in at <http://localhost:3000/login> with `demo@handball-demo.ch` / `demo-handball-2026`.
Logs and pid files are in `$TMPDIR/handball-local` (default `/tmp/handball-local`).
`scripts/local-stack.sh status` and `scripts/local-stack.sh down` do what they say; Postgres and
Redis keep running (stop them with `service postgresql stop`).

Without `HB_WEB_DEV=1` the script runs `next start` if `apps/web/.next` holds a production build
(`pnpm --filter @handball/web build`), which is closer to production and faster for screenshots.

## Verify

- `curl -s localhost:8000/readyz` reports Postgres, Redis and S3 as ok.
- After `make seed`, the worker log shows `run_ingest ... Job OK` and the GPU worker log
  `run_analysis` for the two demo videos.

## Tests and screenshots

- `make test-py` without `make db`: the API tests use `HB_TEST_ADMIN_DSN`
  (default `postgresql://handball:handball@localhost:5432/postgres`), which the host Postgres
  serves. Run `uv run pytest apps packages -n auto`.
- `pnpm test` (Vitest) needs nothing running.
- Playwright: Chromium is preinstalled in cloud sessions. With the stack up,
  `pnpm --filter @handball/web test:e2e` and the screenshot run
  `pnpm --filter @handball/web exec playwright test -c screens.config.ts` work as in compose,
  except checks that read Mailpit (`e2e/helpers.ts`, `linkFromMail`): those need
  `HB_EMAIL_BACKEND=smtp` and a Mailpit binary on port 8025.

## Limits

- moto keeps objects in memory: after `down`, uploaded videos are gone while their database rows
  stay. Run `make seed` against a fresh database (`dropdb handball` as `postgres`) to start over.
- Docker itself may still work for building (`dockerd` can be started by hand); only image pulls
  are rate limited.

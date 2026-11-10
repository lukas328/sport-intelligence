#!/usr/bin/env bash
# Local stack without Docker images: Postgres 16, Redis and an S3 stand-in (moto) from the host,
# API, worker and web as plain processes. For environments where `make up` cannot pull images
# (cloud sessions hit Docker Hub rate limits). See docs/runbooks/local-stack-without-docker.md.
#
#   scripts/local-stack.sh up       # start everything (idempotent)
#   scripts/local-stack.sh down     # stop the processes started here
#   scripts/local-stack.sh status
#   scripts/local-stack.sh restart-web   # after editing apps/web/messages (dev server cache)
#   scripts/local-stack.sh restart-api   # after backend changes (runs the migrations too)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN="${HB_LOCAL_RUN:-${TMPDIR:-/tmp}/handball-local}"
mkdir -p "$RUN"

export HB_ENV=local
export HB_DATABASE_URL=postgresql+asyncpg://handball_app:handball_app@localhost:5432/handball
export HB_MIGRATION_DATABASE_URL=postgresql+asyncpg://handball:handball@localhost:5432/handball
export HB_REDIS_URL=redis://localhost:6379/0
export HB_S3_ENDPOINT_URL=http://localhost:9000
export HB_S3_PUBLIC_ENDPOINT_URL=http://localhost:9000
export HB_S3_ACCESS_KEY=handball
export HB_S3_REGION=us-east-1  # moto needs a LocationConstraint for any other region
export HB_S3_SECRET_KEY=handball-secret
export HB_INTERNAL_TOKEN=dev-only-internal-token
export HB_API_INTERNAL_URL=http://localhost:8000
export HB_CORS_ORIGINS='["http://localhost:3000"]'
export HB_WEB_BASE_URL=http://localhost:3000
export HB_EMAIL_BACKEND=console
export HB_RATE_LIMIT_AUTH="300/60"
export HB_UPLOAD_PART_SIZE=5242880
export HB_GPU_BACKEND=local
export HB_OPERATOR_EMAILS='["@ops-e2e.ch"]'
export HB_S3_PUBLIC_URL=http://localhost:9000
export FORWARDED_ALLOW_IPS="*"

# how each service shows up in the process list (uv and pnpm start child processes, so pid files lie)
pattern() {
  case "$1" in
    s3) echo "moto_server -H 127.0.0.1 -p 9000" ;;
    api) echo "bin/handball-api" ;;
    worker) echo "bin/handball-worker" ;;
    gpu-worker) echo "bin/handball-gpu-worker" ;;
    web) echo "next-server|next dev" ;;
  esac
}

running() { pgrep -f "$(pattern "$1")" >/dev/null; }

start() { # name, command...
  local name="$1"
  shift
  if running "$name"; then
    echo "$name already running"
    return
  fi
  # no file descriptor of the caller stays open in the service (pipes would never close)
  (cd "$ROOT" && exec nohup "$@" >"$RUN/$name.log" 2>&1) </dev/null >/dev/null 2>&1 &
  echo "$name started (log $RUN/$name.log)"
}

stop() {
  if running "$1"; then
    pkill -f "$(pattern "$1")" || true
    echo "$1 stopped"
  fi
}

wait_for() { # url, seconds
  for _ in $(seq 1 "$2"); do
    curl -fsS -m 10 -o /dev/null "$1" 2>/dev/null && return 0
    sleep 1
  done
  echo "timeout waiting for $1" >&2
  return 1
}

up() {
  service postgresql start >/dev/null
  service redis-server start >/dev/null
  # roles and database as in infra/postgres/init (idempotent)
  su postgres -c "psql -q" <<'SQL'
DO $$BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='handball') THEN
    CREATE ROLE handball LOGIN SUPERUSER PASSWORD 'handball'; END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='handball_app') THEN
    CREATE ROLE handball_app LOGIN PASSWORD 'handball_app' NOSUPERUSER NOBYPASSRLS; END IF;
END$$;
SQL
  su postgres -c "psql -lqt" | cut -d'|' -f1 | grep -qw handball || su postgres -c "createdb -O handball handball"
  start s3 uvx --from 'moto[server]==5.1.4' moto_server -H 127.0.0.1 -p 9000
  wait_for http://localhost:9000/moto-api/ 60
  (cd "$ROOT/apps/api" && uv run alembic upgrade head && uv run python -m handball_api.bootstrap)
  start api uv run handball-api
  start worker uv run handball-worker
  start gpu-worker uv run handball-gpu-worker
  wait_for http://localhost:8000/healthz 60
  if [[ ! -f "$ROOT/apps/web/.next/BUILD_ID" || "${HB_WEB_DEV:-}" == "1" ]]; then
    start web pnpm --filter @handball/web dev
  else
    start web pnpm --filter @handball/web start
  fi
  wait_for http://localhost:3000/api/healthz 180
  echo "web http://localhost:3000  api http://localhost:8000  (seed: make seed)"
}


# messages/*.json are cached by the dev server: after editing them, restart it with a clean cache
restart-web() {
  stop web
  sleep 2
  rm -rf "$ROOT/apps/web/.next"
  start web pnpm --filter @handball/web dev
  wait_for http://localhost:3000/api/healthz 180
}

# after backend changes: migrations, then API and workers with the new code
restart-api() {
  stop api
  stop worker
  stop gpu-worker
  sleep 2
  up
}

down() {
  for name in web gpu-worker worker api s3; do stop "$name"; done
}

status() {
  for name in s3 api worker gpu-worker web; do
    if running "$name"; then echo "$name running"; else echo "$name stopped"; fi
  done
}

"${1:-up}"

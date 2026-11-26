#!/usr/bin/env bash
# Deploy only while no analysis runs (rule of the Hauptsitzung). deploy.yml runs this while the
# database is up, before the images, migrations and apply (also before a pause). Lists the
# processing jobs that are queued or running and were updated in the last BUSY_MAX_AGE_H hours
# (older ones are stuck, the watchdog ends them).
#   MODE=deploy: jobs found -> exit 1 with the list, unless FORCE_BUSY=true (then a warning).
#                job list not readable -> exit 1 as well (unknown is not idle), FORCE_BUSY overrides.
#   MODE=plan:   only a notice, never stops the run.
# Reads the database with app.bypass_rls = on (FORCE ROW LEVEL SECURITY, like move-db.sh), through
# a firewall rule for this runner's address that is removed at the end. BUSY_DSN (tests) skips the
# Azure part. Needs: rg, terraform outputs in the cwd (key_vault, postgres_server).
set -euo pipefail
MODE=${MODE:?}
FORCE_BUSY=${FORCE_BUSY:-false}
BUSY_MAX_AGE_H=${BUSY_MAX_AGE_H:-2}
FW_RULE=${FW_RULE:-gh-busy-check}

if [ -n "${BUSY_DSN:-}" ]; then
  dsn=$BUSY_DSN
else
  kv=$(terraform output -raw key_vault)
  pg=$(terraform output -raw postgres_server)
  dsn=$(az keyvault secret show --vault-name "$kv" -n hb-admin-dsn --query value -o tsv)
  echo "::add-mask::$dsn"
  ip=$(curl -fsS https://api.ipify.org)
  trap 'az postgres flexible-server firewall-rule delete -g "$rg" --server-name "$pg" --name "$FW_RULE" --yes -o none || true' EXIT
  az postgres flexible-server firewall-rule create -g "$rg" --server-name "$pg" --name "$FW_RULE" \
    --start-ip-address "$ip" --end-ip-address "$ip" -o none
fi

sql="SELECT coalesce(left(video_asset_id::text, 8), '-'), kind, status,
       to_char(created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI') || ' UTC',
       to_char(updated_at AT TIME ZONE 'UTC', 'HH24:MI') || ' UTC'
     FROM processing_jobs
     WHERE status IN ('queued', 'running')
       AND updated_at > now() - make_interval(hours => $BUSY_MAX_AGE_H::int)
     ORDER BY created_at"
if rows=$(PGOPTIONS="-c app.bypass_rls=on" PGCONNECT_TIMEOUT=20 \
    psql "$dsn" -X -q -v ON_ERROR_STOP=1 -At -F ' | ' -c "$sql" 2>"${RUNNER_TEMP:-/tmp}/busy.err"); then
  :
else
  msg="job list not readable: $(head -1 "${RUNNER_TEMP:-/tmp}/busy.err" | sed "s/^psql: error: //")"
  if [ "$MODE" = deploy ] && [ "$FORCE_BUSY" != true ]; then
    echo "::error::$msg. Deploy stopped (unknown is not idle); force_busy=true deploys anyway."
    exit 1
  fi
  echo "::warning::$msg"
  exit 0
fi

if [ -z "$rows" ]; then
  echo "no analysis queued or running (jobs updated in the last ${BUSY_MAX_AGE_H} h): deploy is safe"
  exit 0
fi
n=$(printf '%s\n' "$rows" | wc -l)
echo "== $n job(s) queued or running (asset | kind | status | since | last update)"
printf '%s\n' "$rows"
if [ "$MODE" != deploy ]; then
  echo "::notice::$n job(s) queued or running: a deploy now would stop them (rule: deploy only while no analysis runs)"
elif [ "$FORCE_BUSY" = true ]; then
  echo "::warning::$n job(s) queued or running, deploying anyway (force_busy=true)"
else
  echo "::error::$n job(s) queued or running: deploy stopped. Wait until they end, or force_busy=true to deploy anyway."
  exit 1
fi

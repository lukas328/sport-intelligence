#!/usr/bin/env bash
# Moves the staging database from the first environment (rg-hb-stg, Switzerland North) into the eu
# environment (docs/plans/staging-umzug-eu.md, step C). Run by the deploy workflow: mode «move-db»,
# stack «eu», working directory infra/terraform/azure with the eu state initialised and $rg set.
#
# 1. Refuses while a job is queued or running in the old database.
# 2. Maintenance: the old web app's ingress goes off (nobody writes any more; the old environment
#    stays otherwise untouched, «ingress enable» brings it back as the way back).
# 3. pg_dump of the old database, pg_restore --clean into the new one (Postgres 16 client in a
#    container). Tables use FORCE ROW LEVEL SECURITY: both sides run with app.bypass_rls = on, the
#    switch the app's system access uses (core/db.py), so dump and restore see every row.
# 4. Row counts of the main tables on both sides must match.
# The only other changes: a firewall rule for this runner's address on both servers, removed at
# the end. Connection strings come from the vaults and are masked, never printed.
set -euo pipefail

OLD_RG=${OLD_RG:-rg-hb-stg}
FW_RULE=${FW_RULE:-gh-move-db}
OUT=${OUT:-$RUNNER_TEMP/move-db}
mkdir -p "$OUT"

new_kv=$(terraform output -raw key_vault)
new_pg=$(terraform output -raw postgres_server)
old_kv=$(az keyvault list -g "$OLD_RG" --query "[0].name" -o tsv)
old_pg=$(az postgres flexible-server list -g "$OLD_RG" --query "[0].name" -o tsv)
old_web=$(az containerapp list -g "$OLD_RG" --query "[?ends_with(name, '-web')].name | [0]" -o tsv)
old_dsn=$(az keyvault secret show --vault-name "$old_kv" -n hb-admin-dsn --query value -o tsv)
new_dsn=$(az keyvault secret show --vault-name "$new_kv" -n hb-admin-dsn --query value -o tsv)
echo "::add-mask::$old_dsn"
echo "::add-mask::$new_dsn"
echo "from $old_pg ($OLD_RG) to $new_pg ($rg); old web app $old_web"

ip=$(curl -fsS https://api.ipify.org)
cleanup() {
  az postgres flexible-server firewall-rule delete -g "$OLD_RG" --server-name "$old_pg" --name "$FW_RULE" --yes -o none || true
  az postgres flexible-server firewall-rule delete -g "$rg" --server-name "$new_pg" --name "$FW_RULE" --yes -o none || true
}
trap cleanup EXIT
az postgres flexible-server firewall-rule create -g "$OLD_RG" --server-name "$old_pg" --name "$FW_RULE" \
  --start-ip-address "$ip" --end-ip-address "$ip" -o none
az postgres flexible-server firewall-rule create -g "$rg" --server-name "$new_pg" --name "$FW_RULE" \
  --start-ip-address "$ip" --end-ip-address "$ip" -o none

pg() { # image command...: Postgres 16 client tools, every row visible (FORCE RLS)
  docker run --rm --network host -e PGOPTIONS="-c app.bypass_rls=on" -e PGCONNECT_TIMEOUT=30 \
    -v "$OUT:/w" postgres:16-alpine "$@"
}
q() { pg psql "$1" -X -v ON_ERROR_STOP=1 -At -c "$2"; }

busy=$(q "$old_dsn" "SELECT count(*) FROM processing_jobs WHERE status IN ('queued', 'running')")
if [ "$busy" != 0 ]; then
  echo "::error::$busy job(s) queued or running in the old database: wait until they end, then run again"
  exit 1
fi

echo "== maintenance: old web app ingress off"
az containerapp ingress disable -g "$OLD_RG" -n "$old_web" -o none

echo "== dump"
pg pg_dump "$old_dsn" --format=custom --enable-row-security --no-owner -f /w/db.dump
ls -l "$OUT/db.dump"

echo "== restore"
pg pg_restore --dbname="$new_dsn" --clean --if-exists --no-owner --exit-on-error \
  --enable-row-security /w/db.dump

echo "== row counts (old | new)"
ok=true
for t in organizations users org_memberships teams matches video_assets processing_jobs events alembic_version; do
  a=$(q "$old_dsn" "SELECT count(*) FROM $t" 2>/dev/null || echo "-")
  b=$(q "$new_dsn" "SELECT count(*) FROM $t" 2>/dev/null || echo "-")
  printf '%-18s %8s | %s\n' "$t" "$a" "$b" | tee -a "$OUT/counts.txt"
  [ "$a" = "$b" ] || ok=false
done
rm -f "$OUT/db.dump"
if [ "$ok" != true ]; then
  echo "::error::row counts differ; the old environment is in maintenance (ingress off): «az containerapp ingress enable -g $OLD_RG -n $old_web --type external --target-port 3000» brings it back"
  exit 1
fi
echo "database moved; the old web app stays in maintenance until DNS points to the new environment"

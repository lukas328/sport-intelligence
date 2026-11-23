#!/usr/bin/env bash
# Read-only diagnosis of the newest finished analysis on staging (deploy.yml, mode status, diag on).
# Collects into $OUT: the gpu-worker log of the last 24 hours (Log Analytics), the asset row with its
# analysis result and jobs (database, row security bypassed for reading), the list of the asset's
# stored files and the main artefacts (play.json, observations.npz, ball.bin, tracks.parquet).
# The only change on Azure is a firewall rule for this runner's address on the database, removed
# again by the caller's cleanup step. Nothing is written to the database or the bucket.
# Needs: rg, OUT, DIAG_ASSET (optional asset id), staging.tfvars and terraform outputs in the cwd.
set -euo pipefail
mkdir -p "$OUT/artefacts"

ws=$(az monitor log-analytics workspace list -g "$rg" --query "[0].customerId" -o tsv)
# One-off questions: every diag-queries/*.kql next to this script runs as a Log Analytics query.
for f in "$(dirname "$0")"/diag-queries/*.kql; do
  [ -e "$f" ] || continue
  n=$(basename "$f" .kql)
  echo "== query $n"
  if az monitor log-analytics query -w "$ws" -o json --analytics-query "$(cat "$f")" >"$OUT/kql-$n.json" 2>"$OUT/kql-$n.err"; then
    jq -r '(.[0] // {} | keys_unsorted | @tsv), (.[] | [.[] | tostring] | @tsv)' "$OUT/kql-$n.json" >"$OUT/kql-$n.tsv" || true
    echo "rows: $(($(wc -l <"$OUT/kql-$n.tsv") - 1))"; cut -c1-500 "$OUT/kql-$n.tsv" | sed -n '1,300p'
  else
    echo "(query failed: $(head -c 300 "$OUT/kql-$n.err"))"
  fi
done
echo "== redis container: args, volume mounts, volumes"
redis_app=$(az containerapp list -g "$rg" --query "[?contains(name,'redis')].name | [0]" -o tsv)
if [ -n "$redis_app" ]; then
  az containerapp show -g "$rg" -n "$redis_app" --query "{args: properties.template.containers[0].args, command: properties.template.containers[0].command, mounts: properties.template.containers[0].volumeMounts, volumes: properties.template.volumes, revision: properties.latestRevisionName}" -o json || true
fi
echo "== worker logs (worker and gpu-worker), last 24 hours"
az monitor log-analytics query -w "$ws" -o json --analytics-query "ContainerAppConsoleLogs_CL
  | where TimeGenerated > ago(24h) | where ContainerAppName_s contains 'worker'
  | project TimeGenerated, ContainerAppName_s, Log_s | order by TimeGenerated asc" >"$OUT/workers-24h.json"
jq -r '.[] | "\(.TimeGenerated) \(.ContainerAppName_s) \(.Log_s)"' "$OUT/workers-24h.json" >"$OUT/workers-24h.log"
echo "lines: $(wc -l <"$OUT/workers-24h.log")"
echo "== analysis_done"
grep 'analysis_done' "$OUT/workers-24h.log" || echo "(none in 24 hours)"
echo "== warnings and errors"
grep -Ei '\[(warning|error|critical) *\]|"level": ?"(warning|error|critical)"|Traceback|Killed|OOM' "$OUT/workers-24h.log" | cut -c1-600 || echo "(none)"

echo "== API requests on upload and video endpoints, last 24 hours (time, method, path with ids masked, status; no addresses)"
az monitor log-analytics query -w "$ws" -o json --analytics-query "ContainerAppConsoleLogs_CL
  | where TimeGenerated > ago(24h) | where ContainerAppName_s contains 'api'
  | where Log_s has_any ('/videos', '/uploads', '/upload', '/parts', 'unhandled_exception')
  | project TimeGenerated, Log_s | order by TimeGenerated asc" >"$RUNNER_TEMP/api-uploads.json"
jq -r '.[] | "\(.TimeGenerated) \(.Log_s)"' "$RUNNER_TEMP/api-uploads.json" \
  | grep -E '"(GET|POST|PUT|PATCH|DELETE) [^"]*(videos|upload|parts)' \
  | sed -E 's/[0-9]{1,3}(\.[0-9]{1,3}){3}(:[0-9]+)?//g; s/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/:id/g; s/\?[^ "]*//g' \
  | sed -E 's/^([^ ]+) .*"([A-Z]+) ([^ ]+) HTTP[^"]*" ([0-9]{3}).*/\1 \2 \3 \4/' | tee "$OUT/api-uploads.txt" | tail -200 || echo "(none)"
kv=$(terraform output -raw key_vault)
dsn=$(az keyvault secret show --vault-name "$kv" -n hb-admin-dsn --query value -o tsv)
echo "::add-mask::$dsn"
ip=$(curl -fsS https://api.ipify.org)
az postgres flexible-server firewall-rule create -g "$rg" --server-name "$(terraform output -raw postgres_server)" \
  --name "$FW_RULE" --start-ip-address "$ip" --end-ip-address "$ip" -o none

q() { PGCONNECT_TIMEOUT=20 psql "$dsn" -v ON_ERROR_STOP=1 -At -c "SET app.bypass_rls = 'on'; $1"; }
echo "== postgres connection slots and who holds them now (staging 17.11.: TooManyConnections)"
q "SELECT 'max_connections=' || current_setting('max_connections')
   || ' superuser_reserved=' || current_setting('superuser_reserved_connections')
   || ' reserved=' || coalesce(current_setting('reserved_connections', true), '-')" || true
q "SELECT u || ' | ' || a || ' | ' || s || ' | ' || count(*) FROM (SELECT coalesce(usename, '-') AS u,
   coalesce(nullif(regexp_replace(application_name, ' [0-9]+$', ''), ''), '-') AS a, coalesce(state, '-') AS s
   FROM pg_stat_activity WHERE backend_type = 'client backend') c GROUP BY u, a, s ORDER BY 1" || true
if [ -n "${DIAG_ASSET:-}" ]; then
  where="id = '${DIAG_ASSET//[^0-9a-f-]/}'"
else
  where="analysis IS NOT NULL ORDER BY updated_at DESC LIMIT 1"
fi
echo "== video assets of the last 24 hours with their jobs"
q "SELECT coalesce(jsonb_agg(to_jsonb(r) ORDER BY r.created_at), '[]'::jsonb) FROM (SELECT v.id, v.match_id,
   v.filename, v.status, v.size_bytes, v.upload_id IS NOT NULL AS multipart_open, v.error, v.created_at,
   v.updated_at, (v.analysis IS NOT NULL) AS has_analysis,
   (SELECT coalesce(jsonb_agg(jsonb_build_object('kind', j.kind, 'status', j.status, 'progress', j.progress,
      'error', j.error, 'created_at', j.created_at, 'updated_at', j.updated_at) ORDER BY j.created_at), '[]'::jsonb)
    FROM processing_jobs j WHERE j.video_asset_id = v.id) AS jobs
   FROM video_assets v WHERE v.created_at > now() - interval '24 hours') r" \
  | tail -1 | jq . | tee "$OUT/recent_assets.json"
# One-off data fixes, only with the input oneoff: every oneoff/*.sql runs in one transaction
# that rolls back on any error (the files check their own row counts first).
if [ "${ONEOFF:-false}" = true ]; then
  for f in "$(dirname "$0")"/oneoff/*.sql; do
    [ -e "$f" ] || continue
    echo "== one-off $(basename "$f")"
    PGCONNECT_TIMEOUT=20 PGOPTIONS="-c app.bypass_rls=on" \
      psql "$dsn" -v ON_ERROR_STOP=1 -X --single-transaction -f "$f" 2>&1 | tee "$OUT/oneoff-$(basename "$f" .sql).txt"
  done
fi
# One-off Azure questions: every diag-queries/*.sh runs here (read-only az commands by convention:
# list, show, query; nothing that creates, updates or deletes).
for f in "$(dirname "$0")"/diag-queries/*.sh; do
  [ -e "$f" ] || continue
  n=$(basename "$f" .sh)
  echo "== az $n (read only)"
  rg="$rg" bash "$f" 2>&1 | tee "$OUT/az-$n.txt" | head -300 || true
done
# One-off database questions: every diag-queries/*.sql runs read-only (no writes possible).
for f in "$(dirname "$0")"/diag-queries/*.sql; do
  [ -e "$f" ] || continue
  n=$(basename "$f" .sql)
  echo "== sql $n (read only)"
  PGCONNECT_TIMEOUT=20 PGOPTIONS="-c default_transaction_read_only=on -c app.bypass_rls=on" \
    psql "$dsn" -v ON_ERROR_STOP=1 -X -f "$f" 2>&1 | tee "$OUT/sql-$n.txt" | head -200 || true
done
echo "== the 8 newest processing jobs (any asset)"
q "SELECT coalesce(jsonb_agg(to_jsonb(r)), '[]'::jsonb) FROM (SELECT id, video_asset_id, kind, status,
   progress, error, created_at, updated_at FROM processing_jobs ORDER BY created_at DESC LIMIT 8) r" \
  | tail -1 | jq . | tee "$OUT/recent_jobs.json"
asset=$(q "SELECT id FROM video_assets WHERE $where" | tail -1)
[ -n "$asset" ] || { echo "no asset found"; exit 1; }
echo "== asset $asset"
q "SELECT row_to_json(r) FROM (SELECT id, organization_id, match_id, role, status, filename,
   size_bytes, storage_key, duration_s, fps, width, height, created_at, updated_at, error
   FROM video_assets WHERE id = '$asset') r" | tail -1 | jq . | tee "$OUT/asset.json"
q "SELECT analysis FROM video_assets WHERE id = '$asset'" | tail -1 >"$OUT/asset_analysis.json"
echo "analysis: $(wc -c <"$OUT/asset_analysis.json") bytes, keys: $(jq -c 'keys' "$OUT/asset_analysis.json")"
jq '.stats // {} | {ball_summary, observe_counters, ball_model_status, reid_model_status, role_model_status}' \
  "$OUT/asset_analysis.json" || true
q "SELECT coalesce(jsonb_agg(to_jsonb(r) ORDER BY r.created_at), '[]'::jsonb) FROM (SELECT id, kind, pipeline_version,
   status, progress, stages, error, created_at, updated_at FROM processing_jobs
   WHERE video_asset_id = '$asset') r" | tail -1 | jq . >"$OUT/jobs.json"
jq -r '.[] | "\(.created_at) \(.kind) \(.status) \(.error // "")"' "$OUT/jobs.json"

org=$(jq -r .organization_id "$OUT/asset.json"); match=$(jq -r .match_id "$OUT/asset.json")
prefix="$org/$match/$asset/"
tfvar() { sed -n "s/^$1 *= *\"\(.*\)\"/\1/p" staging.tfvars; }
endpoint=$(tfvar s3_endpoint_url); bucket=$(tfvar s3_bucket_artifacts); bucket=${bucket:-hb-artifacts}
export AWS_ACCESS_KEY_ID; AWS_ACCESS_KEY_ID=$(tfvar s3_access_key)
export AWS_SECRET_ACCESS_KEY; AWS_SECRET_ACCESS_KEY=$(az keyvault secret show --vault-name "$kv" -n hb-s3-secret-key --query value -o tsv)
echo "::add-mask::$AWS_SECRET_ACCESS_KEY"
export AWS_DEFAULT_REGION=auto
echo "== stored files: bucket $bucket, prefix $prefix"
aws s3 ls --recursive --endpoint-url "$endpoint" "s3://$bucket/$prefix" | tee "$OUT/artefacts.txt" || true
for f in play.json observations.npz ball.bin tracks.parquet; do
  aws s3 cp --only-show-errors --endpoint-url "$endpoint" "s3://$bucket/${prefix}analysis/$f" "$OUT/artefacts/$f" \
    || echo "missing: ${prefix}analysis/$f"
done
printf 'asset=%s\nbucket=%s\nprefix=%s\n' "$asset" "$bucket" "$prefix" >"$OUT/where.txt"
du -sh "$OUT"

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

kv=$(terraform output -raw key_vault)
dsn=$(az keyvault secret show --vault-name "$kv" -n hb-admin-dsn --query value -o tsv)
echo "::add-mask::$dsn"
ip=$(curl -fsS https://api.ipify.org)
az postgres flexible-server firewall-rule create -g "$rg" --server-name "$(terraform output -raw postgres_server)" \
  --name "$FW_RULE" --start-ip-address "$ip" --end-ip-address "$ip" -o none

q() { PGCONNECT_TIMEOUT=20 psql "$dsn" -v ON_ERROR_STOP=1 -At -c "SET app.bypass_rls = 'on'; $1"; }
if [ -n "${DIAG_ASSET:-}" ]; then
  where="id = '${DIAG_ASSET//[^0-9a-f-]/}'"
else
  where="analysis IS NOT NULL ORDER BY updated_at DESC LIMIT 1"
fi
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

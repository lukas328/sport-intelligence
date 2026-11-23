#!/usr/bin/env bash
# Read only: GPU quota, workload profiles and Postgres SKUs in the candidate EU regions, and the
# storage accounts of the staging resource group (move of staging, Integrations-Sitzung 23.11.).
for loc in italynorth swedencentral; do
  echo "== containerapp usages $loc"
  az containerapp list-usages --location "$loc" -o table 2>&1 | head -40 || true
  echo "== containerapp workload profiles supported $loc"
  az containerapp env workload-profile list-supported -l "$loc" -o table 2>&1 | head -40 || true
  echo "== postgres flexible-server burstable SKUs $loc"
  az postgres flexible-server list-skus -l "$loc" \
    --query "[0].supportedServerEditions[?name=='Burstable'].supportedServerSkus[].name" -o tsv 2>&1 | head -20 || true
done
echo "== storage accounts in $rg"
az storage account list -g "$rg" --query "[].{name:name, kind:kind, sku:sku.name, location:location}" -o table 2>&1 || true
for sa in $(az storage account list -g "$rg" --query "[].name" -o tsv 2>/dev/null); do
  echo "== $sa: containers and file shares (names and usage only)"
  az storage container list --account-name "$sa" --auth-mode login --query "[].name" -o tsv 2>&1 | head -20 || true
  az storage share-rm list --storage-account "$sa" -g "$rg" --expand stats --query "[].{name:name, usedBytes:shareUsageBytes, quotaGiB:shareQuota}" -o table 2>&1 | head -20 || true
done
echo "== bucket of the artefacts (from staging.tfvars, host only)"
sed -n 's/^s3_endpoint_url *= *"https\?:\/\/\([^/"]*\).*/\1/p; s/^s3_bucket_[a-z]* *= *"\(.*\)"/bucket \1/p' staging.tfvars || true

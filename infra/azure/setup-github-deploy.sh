#!/usr/bin/env bash
# Run once in Azure Cloud Shell (bash), signed in as the subscription owner:
#
#   curl -fsSL https://raw.githubusercontent.com/lukas328/sport-intelligence/<branch>/infra/azure/setup-github-deploy.sh | bash
#
# It lets GitHub Actions deploy the existing environment (infra/terraform/azure, applied by hand
# before) without any password: an app registration that trusts only this repository's workflow
# runs in the GitHub environment "staging" (OIDC), with the roles terraform needs. It also writes the
# settings terraform was applied with (read back from the running apps) next to the state, so the
# workflow plans against the same values. Nothing secret is printed or stored outside Azure.
# Safe to run again: everything is reused when it exists.
set -euo pipefail

REPO="lukas328/sport-intelligence"
GH_ENV="staging"
APP_NAME="hb-github-deploy"
STATE_RG="rg-hb-tfstate"
APP_RG="${APP_RG:-rg-hb-stg}"
PREFIX="${PREFIX:-hb-stg}"

say() { printf '\n== %s\n' "$*"; }

SUB=$(az account show --query id -o tsv)
TENANT=$(az account show --query tenantId -o tsv)
ME=$(az ad signed-in-user show --query id -o tsv)
MAIL=$(az ad signed-in-user show --query "mail || userPrincipalName" -o tsv)

say "Terraform state"
SA=$(az storage account list -g "$STATE_RG" --query "[0].name" -o tsv)
[ -n "$SA" ] || { echo "No storage account in $STATE_RG. Was terraform applied with README step 2?"; exit 1; }
SA_ID=$(az storage account show -n "$SA" -g "$STATE_RG" --query id -o tsv)
KEY=$(az storage blob list --account-name "$SA" -c tfstate --auth-mode login \
  --query "[?ends_with(name, '.tfstate')].name | [0]" -o tsv)
[ -n "$KEY" ] || { echo "No *.tfstate in $SA/tfstate."; exit 1; }
echo "state: $SA/tfstate/$KEY"

say "Deploy identity for GitHub Actions"
APP_ID=$(az ad app list --display-name "$APP_NAME" --query "[0].appId" -o tsv)
if [ -z "$APP_ID" ]; then
  APP_ID=$(az ad app create --display-name "$APP_NAME" --query appId -o tsv)
fi
SP_ID=$(az ad sp show --id "$APP_ID" --query id -o tsv 2>/dev/null || true)
if [ -z "$SP_ID" ]; then
  SP_ID=$(az ad sp create --id "$APP_ID" --query id -o tsv)
fi
if ! az ad app federated-credential list --id "$APP_ID" --query "[?name=='github-$GH_ENV'].name" -o tsv | grep -q .; then
  az ad app federated-credential create --id "$APP_ID" -o none --parameters "{
    \"name\": \"github-$GH_ENV\",
    \"issuer\": \"https://token.actions.githubusercontent.com\",
    \"subject\": \"repo:$REPO:environment:$GH_ENV\",
    \"audiences\": [\"api://AzureADTokenExchange\"]
  }"
fi
echo "app: $APP_NAME ($APP_ID), trusts repo:$REPO:environment:$GH_ENV"

assign() { # role scope
  if [ -z "$(az role assignment list --assignee "$SP_ID" --role "$1" --scope "$2" --query "[0].id" -o tsv)" ]; then
    for i in 1 2 3 4 5 6; do
      az role assignment create --assignee-object-id "$SP_ID" --assignee-principal-type ServicePrincipal \
        --role "$1" --scope "$2" -o none && return 0
      sleep 10 # a new identity takes a moment to appear
    done
    return 1
  fi
}
# terraform creates resources and role assignments (registry pull, Key Vault) in the subscription
assign "Contributor" "/subscriptions/$SUB"
assign "User Access Administrator" "/subscriptions/$SUB"
assign "Storage Blob Data Contributor" "$SA_ID"
KV_ID=$(az keyvault list -g "$APP_RG" --query "[0].id" -o tsv)
if [ -n "$KV_ID" ]; then
  # terraform reads the secrets it wrote before it can plan
  assign "Key Vault Secrets Officer" "$KV_ID"
fi
echo "roles: Contributor, User Access Administrator (subscription), state blob, Key Vault secrets"

say "Settings the environment was applied with"
api=$(az containerapp show -g "$APP_RG" -n "$PREFIX-api" -o json)
web=$(az containerapp show -g "$APP_RG" -n "$PREFIX-web" -o json)
gpu=$(az containerapp show -g "$APP_RG" -n "$PREFIX-gpu-worker" -o json)
pg=$(az postgres flexible-server list -g "$APP_RG" --query "[0]" -o json)
env_of() { jq -r --arg n "$1" '[.properties.template.containers[0].env[] | select(.name == $n) | .value][0] // empty' <<<"$api"; }
q() { jq -Rn --arg v "$1" '$v'; } # HCL string literal (same quoting as JSON)

known='HB_ENV HB_LOG_JSON HB_REDIS_URL HB_API_INTERNAL_URL HB_WEB_BASE_URL HB_CORS_ORIGINS HB_S3_ENDPOINT_URL HB_S3_PUBLIC_ENDPOINT_URL HB_S3_REGION HB_S3_ACCESS_KEY HB_S3_BUCKET_VIDEOS HB_S3_BUCKET_ARTIFACTS HB_EMAIL_BACKEND HB_EMAIL_FROM HB_SMTP_HOST HB_SMTP_PORT HB_SMTP_USERNAME HB_SMTP_STARTTLS HB_COOKIE_SECURE HB_PWNED_CHECK HB_BILLING_ENFORCE HB_OPERATOR_EMAILS HB_GPU_BACKEND FORWARDED_ALLOW_IPS'
base_secrets='HB_DATABASE_URL HB_SECRET_KEY HB_ENCRYPTION_KEY HB_INTERNAL_TOKEN HB_S3_SECRET_KEY HB_SMTP_PASSWORD'
extra_env=$(jq -c --arg known "$known" '[.properties.template.containers[0].env[]
  | select(.value != null and (.name as $n | ($known | split(" ") | index($n)) == null))
  | {(.name): .value}] | add // {}' <<<"$api")
optional=$(jq -c --arg base "$base_secrets" '[.properties.template.containers[0].env[]
  | select(.secretRef != null and (.name as $n | ($base | split(" ") | index($n)) == null)) | .name]' <<<"$api")

domain=$(env_of HB_WEB_BASE_URL); domain=${domain#https://}
tag=$(jq -r '.properties.template.containers[0].image | split(":") | last' <<<"$api")
bound=$(jq -r '[.properties.configuration.ingress.customDomains // [] | .[] | select(.name == "'"$domain"'")] | length > 0' <<<"$web")
paused=$(jq -r '(.properties.template.scale.minReplicas // 1) == 0' <<<"$api")
budget=$(az consumption budget list --resource-group "$APP_RG" --query "[0]" -o json 2>/dev/null || echo null)
amount=$(jq -r '.amount // 80' <<<"$budget")
alerts=$(jq -c --arg me "$MAIL" '[.notifications // {} | to_entries[] | .value.contactEmails[]?] | unique | if length == 0 then [$me] else . end' <<<"$budget")

smtp_port=$(env_of HB_SMTP_PORT)
operators=$(env_of HB_OPERATOR_EMAILS)
billing=$(env_of HB_BILLING_ENFORCE)

cat >staging.tfvars <<EOF
# Read back from the running environment by infra/azure/setup-github-deploy.sh ($(date -u +%F)).
# The deploy workflow downloads this file; it holds no secrets (they are in Key Vault).
subscription_id       = $(q "$SUB")
name                  = "hb"
environment           = "staging"
location              = $(q "$(az group show -n "$APP_RG" --query location -o tsv)")
app_domain            = $(q "$domain")
bind_custom_domain    = $bound
image_tag             = $(q "$tag")
budget_amount         = $amount
alert_emails          = $alerts
kv_deployer_object_id = $(q "$ME")

postgres_sku         = $(q "$(jq -r '"\(.sku.tier | if . == "Burstable" then "B" elif . == "GeneralPurpose" then "GP" else "MO" end)_\(.sku.name)"' <<<"$pg")")
postgres_storage_mb  = $(jq -r '.storage.storageSizeGb * 1024' <<<"$pg")
postgres_backup_days = $(jq -r '.backup.backupRetentionDays' <<<"$pg")

s3_endpoint_url     = $(q "$(env_of HB_S3_ENDPOINT_URL)")
s3_access_key       = $(q "$(env_of HB_S3_ACCESS_KEY)")
s3_bucket_videos    = $(q "$(env_of HB_S3_BUCKET_VIDEOS)")
s3_bucket_artifacts = $(q "$(env_of HB_S3_BUCKET_ARTIFACTS)")

email_from    = $(q "$(env_of HB_EMAIL_FROM)")
smtp_host     = $(q "$(env_of HB_SMTP_HOST)")
smtp_port     = ${smtp_port:-587}
smtp_username = $(q "$(env_of HB_SMTP_USERNAME)")

operator_emails  = ${operators:-[]}
billing_enforce  = ${billing:-false}
gpu_backend      = $(q "$(env_of HB_GPU_BACKEND)")
extra_env        = $extra_env
optional_secrets = $optional

paused            = $paused
web_min_replicas  = $(jq -r '.properties.template.scale.minReplicas // 1' <<<"$web")
gpu_worker_cpu    = $(jq -r '.properties.template.containers[0].resources.cpu' <<<"$gpu")
gpu_worker_memory = $(q "$(jq -r '.properties.template.containers[0].resources.memory' <<<"$gpu")")
EOF
az storage blob upload --account-name "$SA" -c tfstate -n staging.tfvars -f staging.tfvars \
  --auth-mode login --overwrite -o none
echo "written: $SA/tfstate/staging.tfvars ($(grep -c = staging.tfvars) settings, no secrets)"

say "Done. Copy these five lines back into the chat (none of them is a secret):"
cat <<EOF
AZURE_CLIENT_ID=$APP_ID
AZURE_TENANT_ID=$TENANT
AZURE_SUBSCRIPTION_ID=$SUB
TFSTATE_ACCOUNT=$SA
TFSTATE_KEY=$KEY
EOF

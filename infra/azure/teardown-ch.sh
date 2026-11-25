#!/usr/bin/env bash
# Deletes the first environment (rg-hb-stg, Switzerland North) for good, once the eu environment
# runs (docs/plans/staging-umzug-eu.md, section 7). Run by the deploy workflow: mode «teardown»,
# stack «ch», input «confirm» = the name of the resource group; working directory
# infra/terraform/azure with the ch state initialised and $rg set.
#
# 1. Refuses unless: confirm equals $rg; $rg is not the eu resource group; the app domain does not
#    point to the old web app; the app answers 200 over the domain (so the eu environment serves it).
# 2. Lists what is in the group (log and artefact), then deletes the whole group.
# 3. Purges the old vault from soft delete (secrets gone at once; if the deployer lacks the right,
#    Azure removes it by itself after 7 days).
# The ch state (staging.tfstate) and the state account stay untouched. Until the follow-up change
# (stack eu as the default, stack ch gone) nobody runs plan or deploy with stack «ch»: it would plan
# a new first environment.
set -euo pipefail

: "${CONFIRM:?}" "${rg:?}" "${APP_DOMAIN:?}" "${TFSTATE_ACCOUNT:?}"
OUT=${OUT:-$RUNNER_TEMP/teardown}
EU_STATE=${EU_STATE:-staging-eu.tfstate}
mkdir -p "$OUT"

[ -n "$rg" ] || { echo "::error::the ch state has no resource group (already removed?)"; exit 1; }
if [ "$CONFIRM" != "$rg" ]; then
  echo "::error::confirm must be the resource group name «$rg» (got «$CONFIRM»)"
  exit 1
fi

# the eu resource group from its state: never delete that one
az storage blob download --account-name "$TFSTATE_ACCOUNT" -c tfstate -n "$EU_STATE" \
  -f "$OUT/eu.tfstate" --auth-mode login -o none
eu_rg=$(jq -r '.outputs.resource_group.value // empty' "$OUT/eu.tfstate")
rm -f "$OUT/eu.tfstate"
if [ -z "$eu_rg" ] || [ "$eu_rg" = "$rg" ]; then
  echo "::error::eu resource group «$eu_rg» unknown or the same as «$rg»"
  exit 1
fi

if ! az group show -n "$rg" -o none 2>/dev/null; then
  echo "::error::resource group $rg does not exist"
  exit 1
fi

# DNS: the app domain must point elsewhere than the old web app, and the app must answer
old_web=$(az containerapp list -g "$rg" --query "[?ends_with(name, '-web')].name | [0]" -o tsv)
old_fqdn=$(az containerapp show -g "$rg" -n "$old_web" --query properties.configuration.ingress.fqdn -o tsv 2>/dev/null || true)
old_host=${old_fqdn#*.}  # the environment's default domain (also covers a revision fqdn)
cname=$(dig +short CNAME "$APP_DOMAIN" @1.1.1.1 | sed 's/\.$//')
echo "app domain $APP_DOMAIN → ${cname:-?}; old web app $old_web (${old_fqdn:-no ingress})"
if [ -z "$cname" ] || { [ -n "$old_host" ] && [[ "$cname" == *"$old_host" ]]; }; then
  echo "::error::$APP_DOMAIN still points to the old environment (or has no CNAME): switch DNS first"
  exit 1
fi
if [ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 30 "https://$APP_DOMAIN/api/healthz")" != 200 ]; then
  echo "::error::https://$APP_DOMAIN/api/healthz does not answer 200: the eu environment must serve the app"
  exit 1
fi

echo "== what is deleted ($rg)"
az resource list -g "$rg" --query "[].{name:name, type:type, location:location}" -o table | tee "$OUT/resources.txt"
kv=$(az keyvault list -g "$rg" --query "[0].name" -o tsv)

echo "== delete $rg (takes 10 to 30 min)"
az group delete -n "$rg" --yes
echo "$rg deleted"

if [ -n "$kv" ]; then
  echo "== purge vault $kv"
  if ! az keyvault purge -n "$kv" -o none; then
    echo "::warning::vault $kv not purged (missing right?): Azure removes it after the 7 days of soft delete"
  fi
fi

echo "first environment removed; staging.tfstate kept. Left to do by hand: docs/plans/staging-umzug-eu.md, section 7"

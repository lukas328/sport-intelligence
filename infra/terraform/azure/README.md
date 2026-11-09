# Azure module (ADR 025)

Web, API, workers and Redis on **Azure Container Apps**, the database on **Azure Database for PostgreSQL
Flexible Server**, all in one resource group in `switzerlandnorth`. Video and artifacts stay in
**Cloudflare R2** (ADR 002). Secrets live in **Key Vault**: generated ones are written by Terraform,
external ones (R2, SMTP, Google, Stripe) are written by you with `az` and never pass through tfvars.

```
Browser ──https──▶ web (Next.js, public) ──/v1──▶ api (internal) ──▶ Postgres Flexible (TLS)
   │                                                 │  ▲
   └──presigned PUT/GET──▶ Cloudflare R2 (EU) ◀──────┤  │
                                                     ▼  │
                                  redis (internal TCP) ◀── worker, gpu-worker
```

## What it costs (rough, check the Azure pricing calculator)

| Item | Pilot size | per month |
|---|---|---|
| Postgres Flexible B1ms, 32 GB, 14 days PITR | always on | ~ CHF 15–25 |
| Container Apps: web, api, worker, gpu-worker, redis | min. 1 replica each, mostly idle | ~ CHF 15–45 |
| Container Registry Basic | | ~ CHF 5 |
| Key Vault, Log Analytics (30 days), VNet | small volumes | ~ CHF 1–5 |
| Cloudflare R2 | first 10 GB free, no egress fees | ~ CHF 0–5 |

The budget alert (`budget_amount`, default 80) mails you at 80 % actual and 100 % forecast.

## You need

- An Azure account and subscription, the [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli),
  [Terraform](https://developer.hashicorp.com/terraform/install) ≥ 1.9 and Docker (with BuildKit).
- The domain, with DNS at Cloudflare.
- Cloudflare R2: an API token (**Admin Read & Write** for now, because the migration job creates the
  buckets `hb-videos`, `hb-artifacts` and sets CORS on the video bucket), the access key id and the
  account id. Use the `.eu.` endpoint so the buckets get EU jurisdiction.
- An e-mail provider with SMTP (Postmark, ADR 009) and SPF, DKIM, DMARC on the domain.

## 1. Sign in

```bash
az login
```

```bash
az account show --query id -o tsv
```

## 2. State storage (once)

```bash
az group create -n rg-hb-tfstate -l switzerlandnorth
```

```bash
az storage account create -n sthbtfstate$RANDOM -g rg-hb-tfstate -l switzerlandnorth --sku Standard_LRS --min-tls-version TLS1_2 --allow-blob-public-access false
```

Note the account name, then create the container and give yourself access:

```bash
az storage container create --account-name <account> -n tfstate --auth-mode login
```

```bash
az role assignment create --role "Storage Blob Data Contributor" --assignee $(az ad signed-in-user show --query id -o tsv) --scope $(az storage account show -n <account> --query id -o tsv)
```

Copy `backend.hcl.example` to `backend.hcl` and `terraform.tfvars.example` to `terraform.tfvars`, fill
them in (both are git-ignored), then:

```bash
terraform init -backend-config=backend.hcl
```

## 3. Registry and Key Vault first

The apps can only start once their images exist, so the first apply creates just the registry and the vault:

```bash
terraform apply -target=azurerm_container_registry.this -target=azurerm_key_vault_secret.manual -target=azurerm_key_vault_secret.generated
```

Build and push the four images from the repository root (tag = short commit):

```bash
ACR=$(terraform -chdir=infra/terraform/azure output -raw registry) TAG=$(git rev-parse --short HEAD) && az acr login -n ${ACR%%.*} && for app in api worker gpu-worker web; do docker buildx build --platform linux/amd64 -f apps/$app/Dockerfile -t $ACR/hb-$app:$TAG --push .; done
```

Set `image_tag` in `terraform.tfvars` to that tag.

Without Docker (no admin rights on the PC), let the registry build the images. `az acr build` has no
BuildKit (the Dockerfiles use `RUN --mount`), so use the task file, and upload a clean export of the
tracked files only (the working tree holds `.terraform/` with 250 MB of providers and your tfvars):

```bash
TAG=$(git rev-parse --short HEAD) CTX=$(mktemp -d) && git archive HEAD | tar -x -C $CTX && az acr run -r $(terraform -chdir=infra/terraform/azure output -raw registry_name) -f infra/terraform/azure/acr-build.yaml --set tag=$TAG --timeout 7200 $CTX
```

## 4. External secrets

Type the values instead of pasting them into the command, so they stay out of the shell history:

```bash
KV=$(terraform output -raw key_vault) && read -rsp "R2 secret key: " V && az keyvault secret set --vault-name $KV -n hb-s3-secret-key --value "$V" -o none; unset V
```

```bash
KV=$(terraform output -raw key_vault) && read -rsp "SMTP password: " V && az keyvault secret set --vault-name $KV -n hb-smtp-password --value "$V" -o none; unset V
```

## 5. Everything else, then migrate

```bash
terraform apply
```

```bash
az containerapp job start -n $(terraform output -raw migrate_job) -g $(terraform output -raw resource_group)
```

The job creates the runtime role `handball_app` (no BYPASSRLS, ADR 005), runs `alembic upgrade head` and
`handball_api.bootstrap` (buckets and CORS). Logs: Azure portal → the job → Execution history.
Run it again after every deploy that contains a new migration.

**Optional settings** such as Sign in with Google: put the secret into Key Vault under the variable name
in lowercase with dashes, list the variable in `optional_secrets`, add the non-secret part to `extra_env`
and apply:

```bash
KV=$(terraform output -raw key_vault) && read -rsp "Google client secret: " V && az keyvault secret set --vault-name $KV -n hb-google-client-secret --value "$V" -o none; unset V
```

```hcl
extra_env        = { HB_GOOGLE_CLIENT_ID = "123.apps.googleusercontent.com" }
optional_secrets = ["HB_GOOGLE_CLIENT_SECRET"]
```

The same works for Apple (`HB_APPLE_PRIVATE_KEY`), Stripe, `HB_ANTHROPIC_API_KEY` and `HB_SENTRY_DSN`.
Redirect URI for Google and Apple: `https://<app_domain>/v1/auth/oauth/<google|apple>/callback`.

## 6. Custom domain with a managed certificate

In Cloudflare DNS (record **DNS only**, grey cloud, so Azure can issue the certificate):

| Type | Name | Value |
|---|---|---|
| CNAME | `app` | `terraform output -raw web_default_fqdn` |
| TXT | `asuid.app` | `terraform output -raw custom_domain_verification_id` |

Then set `bind_custom_domain = true`, run `terraform apply`, and bind the free managed certificate:

```bash
az containerapp hostname bind -g $(terraform output -raw resource_group) -n $(terraform output -raw web_app) --hostname <app_domain> --environment $(terraform output -raw container_app_environment) --validation-method CNAME
```

## Deploying a new version

Build and push with a new tag (step 3), set `image_tag`, `terraform apply`, then start the migration job
if the release has a migration. A GitHub Actions workflow with OIDC login is the next step (ADR 025).

## Pause (test environment)

Set `paused = true` and `terraform apply`: every app goes to 0 replicas and costs nothing. Stop the
database as well (Azure starts a stopped server again by itself after 7 days):

```bash
az postgres flexible-server stop -g $(terraform output -raw resource_group) -n $(terraform output -raw postgres_server)
```

To resume: `az postgres flexible-server start ...`, `paused = false`, `terraform apply`. While paused only
the registry (~ CHF 5), Postgres storage (~ CHF 4) and a few cents for Key Vault and logs remain.

## Known limits

- `HB_GPU_BACKEND=local`: the analysis runs on the CPU of the gpu-worker container. Slow but enough for
  the pilot; the Modal backend is not implemented yet (`apps/gpu-worker/.../backends/base.py`).
- Redis keeps no data on restart. Queued jobs are lost if the container restarts; this is acceptable
  for the pilot (ADR 001 keeps state in Postgres).
- Postgres accepts connections from all Azure services (TLS and long passwords). Private access in the
  VNet is the next hardening step.
- Not yet covered: off-site backup bucket and scheduled `backup.sh`, alerts from `infra/monitoring/alerts.md`.

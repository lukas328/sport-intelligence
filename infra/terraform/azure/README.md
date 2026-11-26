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
- E-mail: Azure Communication Services, created by Terraform (sending domain = the site's domain,
  data in Switzerland). Its DNS records are set by hand, see «E-mail» below. SMTP stays possible
  (`HB_EMAIL_BACKEND=smtp`, secret `hb-smtp-password`).

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
tracked files only (the working tree holds `.terraform/` with 250 MB of providers and your tfvars).
`.dockerignore` leaves out `infra/`, so copy the task file to the root of the export:

```bash
TAG=$(git rev-parse --short HEAD) CTX=$(mktemp -d) && git archive HEAD | tar -x -C $CTX && cp infra/terraform/azure/acr-build.yaml $CTX/ && az acr run -r $(terraform -chdir=infra/terraform/azure output -raw registry_name) -f acr-build.yaml --set tag=$TAG --timeout 7200 $CTX
```

## 4. External secrets

Type the values instead of pasting them into the command, so they stay out of the shell history:

```bash
KV=$(terraform output -raw key_vault) && read -rsp "R2 secret key: " V && az keyvault secret set --vault-name $KV -n hb-s3-secret-key --value "$V" -o none; unset V
```

```bash
KV=$(terraform output -raw key_vault) && read -rsp "SMTP password: " V && az keyvault secret set --vault-name $KV -n hb-smtp-password --value "$V" -o none; unset V
```

## E-mail (Azure Communication Services)

Terraform creates the mail service, the sending domain (`mail_domain`, default: the domain of
`app_domain`) with the sender `noreply@…` («Handball Intelligence») and the communication
service; its access key goes to the Key Vault (`hb-acs-connection-string`). Then:

1. Set the DNS records of `terraform output mail_verification_records` at Cloudflare (DNS only):
   TXT on the domain (verification and SPF; if the domain has an SPF record already, add
   `include:spf.protection.outlook.com` to it), the two DKIM CNAMEs, and a DMARC TXT on `_dmarc`.
2. Deploy. The step «Mail domain» asks Azure to verify each record and waits up to ten minutes.
   Once domain, SPF, DKIM and DKIM2 are verified, it sets `mail_live`: Terraform links the domain
   and switches the apps to `HB_EMAIL_BACKEND=acs` (this overrides a «console» backend in
   `extra_env`). Until then the apps keep their mail setting.

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

The bootstrap only writes what is missing. With an object-scoped storage key (R2 "Object Read & Write")
it cannot create buckets or set CORS: the job still succeeds and logs `bootstrap_manual_step` with what to
do by hand (create the bucket, or set the printed CORS rule on the video bucket). A bucket that is missing
and cannot be created fails the job (`bootstrap_failed`).

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

Non-secret settings that belong to the code, such as the analysis models (`HB_REID_MODEL` and
`HB_ROLE_MODEL` empty: ReID was trained on MSMT17, research only, licence inventory; the role model
is off), live in `infra/azure/staging-env.json`. Every deploy merges that file into `extra_env` of
the stored settings file; a key set to `null` there is removed. The ball nets are Terraform
variables (`cpu_ball_model*` for the CPU app, `gpu_ball_model*` for the GPU job), since 26.11.2026
hr-nods without DeepSport data (hr1/hrp1 before were non-commercial).

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

## 7. Video straight from R2 (ADR 002 point 7)

With `media_direct = true` (the default) the API still serves the HLS playlists, with the same access
checks as before, but writes presigned R2 URLs for the segments into them (`HB_MEDIA_DIRECT=true`). The
video bytes then go from R2 to the browser and never through the API, the web proxy or Azure egress.
Without it (`media_direct = false`), segments are read through the API as in development.

The browser loads segments from the R2 endpoint (`s3_endpoint_url`) with CORS, so the video bucket needs
this rule. The migration job sets it when its token may (Admin Read & Write); with an object-scoped token
it logs it as `bootstrap_manual_step`. By hand: Cloudflare dashboard → R2 → `hb-videos` → Settings →
CORS policy, with your app origin (both `https://<app_domain>` and the default FQDN while you use it):

```json
[
  {
    "AllowedOrigins": ["https://<app_domain>"],
    "AllowedMethods": ["GET", "HEAD", "PUT"],
    "AllowedHeaders": ["*"],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 3600
  }
]
```

`PUT` and `ETag` are for the direct uploads, `GET`/`HEAD` with any header (`Range`) for playback. The web
CSP allows the R2 origin in `connect-src` and `media-src` (`HB_S3_PUBLIC_URL`, set from
`s3_endpoint_url`). A segment URL stays valid at least `HB_MEDIA_DIRECT_TTL_S` (default 4 h, set it in
`extra_env` to change); the player loads the playlist again when one has expired. That is also how long
a viewer of a revoked share link can keep playing the segments already in the loaded playlist.

Check after the first apply: open a match, DevTools → Network: `index.m3u8` from the app domain,
`init.mp4` and `seg_*.m4s` from `*.eu.r2.cloudflarestorage.com` with status 200 or 206.

## Deploying a new version

Build and push with a new tag (step 3), set `image_tag`, `terraform apply`, then start the migration job
if the release has a migration. A GitHub Actions workflow with OIDC login is the next step (ADR 025).

## Pause (test environment)

Set `paused = true` and `terraform apply`: every app goes to 0 replicas and costs nothing (web and api
scale in on HTTP; the workers and Redis get a cron scale rule that is active one minute a year, because
without any rule they keep one replica despite `min_replicas = 0`). Scale-in takes about 5 minutes.
Stop the database last, after the apply (Azure starts a stopped server again by itself after 7 days).
While it is stopped, `terraform plan` fails to read the server; start it first or plan with
`-refresh=false` for app-only changes:

```bash
az postgres flexible-server stop -g $(terraform output -raw resource_group) -n $(terraform output -raw postgres_server)
```

To resume: `az postgres flexible-server start ...`, `paused = false`, `terraform apply`. While paused only
the registry (~ CHF 5), Postgres storage (~ CHF 4) and a few cents for Key Vault and logs remain.

## Serverless GPU and the second environment (stack «eu»)

Switzerland North has no serverless GPU, so the staging environment moves to Sweden Central
(`docs/plans/staging-umzug-eu.md`). The same module builds it with other settings:

- `name = "hbeu"` (the resource group `rg-hbeu-stg` must be new), `location = "swedencentral"`,
  `mail_data_location = "Europe"`, `kv_runner_role = true`; `gpu = false` at first (the CPU app
  analyses as before) and `gpu = true` in `staging-eu.tfvars` once Azure granted the T4 quota;
- `gpu = true` adds the workload profile `Consumption-GPU-NC8as-T4` and the job `<prefix>-gpu`
  (image `hb-gpu-worker-cuda`, built by `acr-build-cuda.yaml`) instead of the always-on CPU app
  `gpu-worker`. KEDA starts one execution while the Redis list `rq:queue:gpu` is not empty; it runs
  the worker with `--burst` (works the queue, then ends): no cost while nothing waits, a running
  analysis is never stopped by scaling in. Videos longer than `gpu_max_video_minutes` (15) end as
  «too long»; own monthly budget `gpu_budget_amount` (30) with an alert at `gpu_budget_warn` (20);
- `hb-secret-key` and `hb-encryption-key` are written once and never overwritten by Terraform: the
  bootstrap copies the first environment's values, so sessions and encrypted columns stay valid.

Since 25.11.2026 the eu environment is the only one: the first (`rg-hb-stg`, Switzerland North,
state `staging.tfstate`) was deleted with `mode = teardown` (`infra/azure/teardown-ch.sh`), and
`stack = eu` is the workflow's default. `stack = ch` only allows `status` and `teardown`.

GitHub Actions: Deploy with `stack = eu`; `mode = bootstrap` the first time (derives
`staging-eu.tfvars` from `staging.tfvars`, own state `staging-eu.tfstate`, builds vault and
registry, copies the secrets, then deploys like `deploy`). The T4 quota («Managed Environment
Consumption T4 GPUs») shows on the environment's Quota page once the environment exists.

## Alerts

`monitoring = true` (default) creates the alerts listed in `infra/monitoring/alerts.md` (section
«Azure»): health probe of the app domain with the certificate check (only where the domain is bound),
API errors, failed jobs, out-of-memory kills and database storage, by e-mail to `alert_emails`.

## Known limits

- `HB_GPU_BACKEND=local`: the analysis runs on the CPU of the gpu-worker container. Slow but enough for
  the pilot; a Modal backend is not implemented yet.
- Redis writes an append-only file to a small Azure Files share (`azurerm_storage_share.redis`), so
  queued jobs survive a restart of its replica. The API watchdog also enqueues again a job that waits
  but is missing from the queue (`progress.requeue_lost`).
- Postgres connections: the API's processes x max replicas x (pool + overflow) plus
  `postgres_spare_connections` must fit `postgres_user_connections` (check `db_connections`, part of
  every plan). Postgres logs and metrics go to Log Analytics (`diag-postgres`, with
  `log_connections`); `infra/azure/diag-queries/postgres-connections.kql` and the diagnosis show who
  holds the connections.
- Postgres accepts connections from all Azure services (TLS and long passwords). Private access in the
  VNet is the next hardening step.
- Not yet covered: off-site backup bucket and scheduled `backup.sh`, alerts from `infra/monitoring/alerts.md`.

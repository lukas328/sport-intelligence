# 025. App hosting on Azure Container Apps, Postgres Flexible Server

- Status: accepted (owner decision 2026-11-09, answers Q-INFRA-1 for app and database)
- Date: 2026-11-09

## Context
ADR 002 settled object storage (Cloudflare R2, EU) and left the app, Postgres and Redis provider open,
with "EU, cheapest option with managed Postgres and PITR" as the rule. The owner knows Azure best and
will run the platform alone at first; operating effort weighs more than a few francs per month.
The stack is container based (Dockerfiles for web, api, worker, gpu-worker) and needs managed
Postgres 16 with RLS, `pgcrypto` and `citext`, a Redis for the job queue and TLS on a custom domain.

## Decision
1. **Azure, region Switzerland North** (`location` variable; `germanywestcentral` as the EU alternative).
   Data in Switzerland satisfies the EU requirement of ADR 002 (adequacy both ways).
2. **Azure Container Apps** (workload-profile environment, Consumption profile, own VNet) for web
   (public ingress), api (internal ingress, reached only through the web `/v1` proxy), worker,
   gpu-worker and Redis (internal TCP ingress, no persistence). Migrations run as a manual Container
   Apps job that also creates the `handball_app` runtime role.
3. **Azure Database for PostgreSQL Flexible Server** 16, B1ms for the pilot, 14 days PITR.
4. **Key Vault** for every secret; apps read them through one user-assigned identity. Terraform
   generates the internal secrets; the owner writes external ones with `az`, never through tfvars.
5. **Object storage stays on Cloudflare R2** and **GPU compute stays behind `GpuBackend`** (ADR 002).
   Azure Blob and Azure GPUs are not used (no S3 API, egress fees; GPU price and quota).
6. Terraform module `infra/terraform/azure`, state in an Azure storage account, budget alert on the
   resource group.

## Consequences
- Rough pilot cost CHF 40–80 per month (README of the module); scales with replicas and the DB SKU.
- Azure (Microsoft) and Cloudflare are sub-processors; DPA and sub-processor list must name both.
- Until the Modal backend exists, `HB_GPU_BACKEND=local` runs the analysis on container CPUs: slow,
  acceptable for the pilot, measured against P10 before go-live.
- Redis loses queued jobs on a restart; acceptable while state lives in Postgres (ADR 001).
- Follow-ups: private Postgres access in the VNet, GitHub Actions deploy with OIDC, off-site backup
  with scheduled `backup.sh`, alerts from `infra/monitoring/alerts.md` in Azure Monitor, a
  read-only R2 token for the apps once the buckets exist.

## Alternatives considered
- **Hetzner** (cheapest, EU): no managed Postgres; backups and patching would be the owner's job.
- **Scaleway / Exoscale EU**: managed Postgres and serverless containers, but unknown to the owner.
- **Azure App Service**: one container per plan, less fitting for background workers than Container Apps.
- **Azure Kubernetes Service**: more control than needed, fixed node cost.

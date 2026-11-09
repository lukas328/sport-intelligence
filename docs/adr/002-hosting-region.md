# 002. Hosting and data region: EU is enough, cost first, provider abstracted

- Status: accepted (owner decisions 2026-11-03: storage; 2026-11-04: app platform Azure West Europe)
- Date: 2026-11-02, revised 2026-11-03 and 2026-11-04

## Context
Customers are Swiss and German clubs, many with minors (BRIEF 12). The first proposal kept all data in
Switzerland (Exoscale, Infomaniak, AWS Zurich). The owner decided on 2026-11-03: **data in the EU is
enough; the main criteria are cost, simplicity and a choice that holds long term.** This deviates from
BRIEF 6.2 ("Schweiz oder EU", Swiss candidates) only in that Switzerland is no longer preferred; EU stays
the hard requirement (Swiss DSG recognises the EU as adequate).

For a video product, egress (playback, HLS segments, downloads, clip exports) dominates storage cost and
grows with every club; storage itself is cheap.

## Decision
1. **Object storage: Cloudflare R2 with EU jurisdiction** (bucket data stored and processed in the EU).
   No egress fees, free tier for the first 10 GB, S3-compatible, so the code stays plain boto3 with
   `endpoint_url` (ADR 006). Region name for boto3 is `auto`.
2. **First use: shared test videos.** Bucket `handball-testdata`, synced with `scripts/testdata.py`;
   the repo holds only `ml/eval/golden_set/manifest.json` (Q-DATA-1). Two tokens: read/write for the
   owner, read-only for CI and agent sessions.
3. **Application, Postgres, Redis, secrets, monitoring: Microsoft Azure** (owner decision 2026-11-04).
   The owner knows Azure and wants one platform for operations, secrets (Key Vault) and cost control
   (budgets). Services: Container Apps (web, API, workers), Azure Database for PostgreSQL Flexible
   Server (PITR), Redis, Key Vault, Container Registry, Log Analytics; deploys from GitHub Actions
   with OIDC (no stored password). Video files stay in R2 (point 1) because Azure bills egress per GB.
   *Region changed 2026-11-09:* Switzerland North instead of West Europe (ADR 025, `infra/terraform/azure`).
4. **GPU compute behind `GpuBackend`** (`local`, `runpod`, `modal`, `k8s`). The GPU provider must
   process customer video in the EU under a DPA.
5. `Organization.data_region` stays (`ch`, `eu`); until a Swiss bucket exists, both map to the EU bucket.
6. Infrastructure as code in `infra/terraform` with one module per provider behind the same outputs.
7. **Video delivery must not pass through Azure** to keep the R2 egress advantage: today HLS playlists
   and segments are read by the API and streamed through the web proxy (ADR 011), so every watched
   gigabyte would be Azure egress. Before production, segments are served from R2 directly
   (short-lived presigned URLs or a Cloudflare-cached custom domain with signed tokens), the API keeps
   the authorisation check and the playlist.

## Consequences
- Local development and CI stay provider-free (docker compose, SeaweedFS). Nothing in domain code
  refers to a provider; switching to Hetzner Object Storage, Scaleway or a Swiss provider is
  configuration plus a data copy.
- Cloudflare is a US company: the DPA and EU jurisdiction setting must be in place before customer
  video is stored, and Cloudflare is listed as a sub-processor. Clubs that demand Swiss hosting would
  need a Swiss bucket (`data_region = ch`), added later on demand.
- The privacy policy and DPA templates name EU hosting, not "Switzerland only".

## To verify before production
- R2: presigned multipart upload and presigned GET for HLS behave as with SeaweedFS (integration tests
  from M2 against an R2 bucket); object lock or a second bucket for backups.
- Managed Postgres with RLS and PITR at the chosen app provider; GPU price per match (< CHF 2).

## Alternatives considered
- **Exoscale / Infomaniak (CH):** data in Switzerland, but egress is billed and storage costs more;
  the Swiss-only requirement was dropped.
- **Hetzner Object Storage (DE):** cheap, EU company, flat monthly base fee; good fallback, and the
  natural choice if the app servers also go to Hetzner.
- **Azure Blob Storage:** not S3-compatible, would need a storage abstraction in API and workers, and
  egress is billed.
- **AWS S3 (Frankfurt/Zurich):** reliable, but egress costs make video delivery expensive.

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
   *Done 2026-11-20 (`HB_MEDIA_DIRECT`, on in `infra/terraform/azure` via `media_direct`):* the API
   serves the playlists as before and writes presigned R2 GET URLs for the init and media segments into
   them; see «Addendum: direct segment delivery» below.

## Addendum: direct segment delivery (point 7, 2026-11-20)
- **Playlists stay with the API**, with the same checks (tenant, guardian access, share links and their
  scope, native-app media tokens) and the same join over a match's parts. Only the URIs of `init.mp4` and
  `*.m4s` change: each becomes a presigned GET on the public storage endpoint
  (`HB_S3_PUBLIC_ENDPOINT_URL`). Only files of the video's own media folder are signed, never originals or
  the analysis proxy. What a playlist does not list (another video, a match outside a share link) is not
  signed, so access is decided exactly where it was.
- **Presigned S3 URLs, not a custom domain with tokens.** R2 presigned URLs work on the S3 endpoint
  only; R2 has no egress fees, so a CDN in front is not needed for cost. A Cloudflare custom domain with
  signed tokens (WAF rule) stays the option for caching close to the viewer (GO_LIVE: CDN for HLS).
- **Expiry:** a URL is valid at least `HB_MEDIA_DIRECT_TTL_S` (default 4 h). The signing time is rounded
  down to a window (an eighth of the lifetime, at most 1 h), so the same segment has the same URL for that
  window and the browser cache hits across playlist reloads. A longer pause costs one reload: the web
  player loads the playlist again at the same moment on a network error. Trade-off: segments of a loaded
  playlist keep playing up to that long after a share link is revoked.
- **Signing** is our own SigV4 query signer (`core/presign.py`, tested equal to boto3): a full match lists
  over a thousand segments per variant and boto3 needs about 0.3 ms per URL.
- **Browser:** the bucket CORS rule (GET/HEAD, any header for `Range`) is set by the bootstrap or by hand
  (`infra/terraform/azure/README.md`, step 7); the CSP allows the storage origin in `connect-src` and
  `media-src`; the players load with `crossorigin="anonymous"` because Chrome's native HLS stops on
  cross-origin segments otherwise (verified locally with SeaweedFS, hls.js and native). Offline
  presentation packs cache presigned segments under their full URL; the service worker serves them.
- **Fallback:** with `HB_MEDIA_DIRECT=false` (default in development and tests) segments are read through
  the API as before; the API path also keeps answering segment requests when the setting is on.

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

## Addendum 2026-11-24: region Sweden Central

Staging ("hbeu-stg", app.handball-intelligence.com) moved from Switzerland North to **Sweden Central**
on 2026-11-24: Switzerland North offers no serverless GPUs (Consumption-GPU-NC8as-T4), Sweden Central
does. App, database, Redis, Key Vault, monitoring and the GPU job are now in the EU (Sweden); videos and
artefacts stay in Cloudflare R2 (EU). Switzerland recognises the EU as providing adequate data
protection (FADP). The data-location texts on the website, in the help and in the privacy policy are
updated. Plan and steps: `docs/plans/staging-umzug-eu.md`.

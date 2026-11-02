# 002. Hosting and data region: Switzerland first, provider abstracted

- Status: proposed (needs owner decision, see OPEN_QUESTIONS Q-INFRA-1)
- Date: 2026-11-02

## Context
Customers are Swiss and German clubs, many with minors (BRIEF 12). Data must stay in Switzerland or the
EU, the data region is stored per organisation. The pipeline needs GPUs (L4 class, BRIEF 6.3 point 7)
that scale to zero. Candidates named in the brief: Exoscale, Infomaniak, AWS eu-central-2 (Zurich).

## Decision (proposal)
1. **Application, Postgres, Redis and object storage in Switzerland.** Preferred: Exoscale (Swiss
   provider, managed Postgres (DBaaS), S3-compatible SOS storage, SKS Kubernetes) or Infomaniak Public
   Cloud. AWS eu-central-2 as fallback if managed services or GPU capacity in CH are insufficient.
2. **GPU compute behind `GpuBackend`** (`local`, `runpod`, `modal`, `k8s`). The GPU provider must
   process data in CH/EU under a DPA. US-only providers are excluded for customer video.
3. `Organization.data_region` (`ch`, `eu`) selects bucket and GPU pool from M1 on.
4. Infrastructure as code in `infra/terraform` with one module per provider behind the same outputs.

## To verify before acceptance
- GPU instance availability, price per hour and scale-to-zero latency per provider in CH and EU
  (benchmark with `ml/eval/bench.py` from M3). Target: < CHF 2 per match.
- Managed Postgres with RLS support and PITR backups; S3 multipart + presigned URLs; CDN for HLS.
- Contract terms (DPA/AVV) and sub-processor lists.

## Consequences
Local development and CI are provider-free (docker compose). Nothing in domain code refers to a provider.

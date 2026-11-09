# Terraform

Production infrastructure, one module per provider with identical outputs.

- Storage: Cloudflare R2 with EU jurisdiction (ADR 002), buckets created by the migration job.
- App, Postgres, Redis, secrets: [`azure/`](azure/README.md) (ADR 025).

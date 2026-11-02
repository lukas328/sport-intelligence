# 006. Local object storage: SeaweedFS instead of MinIO

- Status: accepted
- Date: 2026-11-02

## Context
The brief names MinIO for local S3. MinIO stopped publishing community container images in 2025;
the Docker Hub repository is no longer pullable. We only need an S3-compatible endpoint locally and
in CI; production uses the provider's object storage (ADR 002).

## Decision
Use **SeaweedFS** (Apache-2.0) in single-container mode with its S3 gateway on port 9000
(`infra/docker-compose.yml`, credentials in `infra/seaweedfs/s3.json`, local only). Buckets are
created idempotently by `python -m handball_api.bootstrap` after migrations.

## Consequences
All code talks plain S3 via boto3 with `endpoint_url`; switching to Garage, MinIO (self-built) or a
cloud bucket is configuration only. S3 multipart and presigned URLs are covered by integration tests in M2.

# 001. Job queue: Redis + RQ, pipeline graph in our own code

- Status: accepted
- Date: 2026-11-02

## Context
The analysis pipeline (BRIEF 7.2) has ~18 stages with declared inputs and outputs. Each stage must be
idempotent, checkpointed on object storage, restartable from the last successful stage, and only the
stages downstream of a change may rerun (BRIEF 6.3 point 6). Some stages run on a GPU worker that
scales to zero, the rest on CPU workers. The brief asks for RQ or Celery.

## Decision
- **RQ** (Redis Queue) as the execution layer. Queues: `default`, `pipeline` (CPU), `gpu`.
- Orchestration (which stage runs next, caching, partial reprocessing) lives in our own code:
  `handball_worker.pipeline.PipelineGraph` derives order and dependencies from declared artifacts,
  computes a cache key per stage (inputs hash + stage version + config), and computes the downstream
  set for a change. State is persisted in Postgres (`ProcessingJob`, from M3), not in the broker.
- Each stage is a plain function enqueued as an RQ job; retries via RQ `Retry`, scheduling via the
  built-in scheduler.

## Consequences
- Simple, typed, easy to test locally (fakeredis, `SimpleWorker`).
- We own the DAG semantics (good: it is a core domain concept; cost: ~200 lines we maintain).
- RQ has no native chords/canvas. Fan-out of video chunks (BRIEF 6.3 point 5) is done by the
  orchestrator enqueueing N chunk jobs and a merge job with `depends_on`.
- If we outgrow RQ, the graph is broker-agnostic; only the enqueue adapter changes.

## Alternatives considered
- **Celery**: richer canvas, but heavier config, weaker typing, and canvas state lives in the broker,
  which conflicts with "restart from last checkpoint" and partial reprocessing kept in Postgres.
- **Temporal / Prefect / Dagster**: strong orchestration, but an extra service to run and operate in a
  Swiss/EU hosting setup. Revisit if pipelines become long-running multi-day workflows.

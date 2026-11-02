# 007. Monorepo tooling: uv workspace + pnpm workspace + Makefile

- Status: accepted
- Date: 2026-11-02

## Decision
- Python 3.12: one **uv** workspace (`apps/api`, `apps/worker`, `apps/gpu-worker`, `packages/court`),
  one lockfile, ruff (lint + format), mypy strict, pytest with an 80 % coverage gate, import-linter for
  module boundaries (apps independent, API layers routers > services > core, court is a leaf).
- TypeScript: **pnpm** workspace, TypeScript strict, ESLint (next config), Vitest, Playwright, madge for
  circular dependencies.
- **Makefile** as the single entry point (`make up`, `make test`, `make lint`, `make typecheck`).
- Shared definitions that both languages need (court geometry, later zones and metric types) come from
  one JSON source with a generator and a CI freshness check.
- No Nx/Turborepo for now; revisit when CI time exceeds ~10 minutes.

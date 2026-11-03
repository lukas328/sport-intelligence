SHELL := /bin/bash
.DEFAULT_GOAL := help
PY_SRC := apps/api/src apps/worker/src apps/gpu-worker/src packages/court/handball_court packages/vision/handball_vision packages/jobkit/handball_jobkit packages/metrics/handball_metrics
PY_TESTS := apps/api/tests apps/worker/tests apps/gpu-worker/tests packages/court/tests packages/vision/tests packages/metrics/tests

help: ## Show targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

install: ## Install Python (uv) and JS (pnpm) dependencies, pre-commit hooks
	uv sync --all-packages
	pnpm install
	uv run pre-commit install

up: ## Start the full local stack (docker compose)
	docker compose up -d --build

down: ## Stop the local stack
	docker compose down

logs: ## Follow logs
	docker compose logs -f --tail=100

court: ## Regenerate court geometry from packages/court/spec/court.json
	uv run python packages/court/scripts/generate.py

api-client: ## Export OpenAPI and regenerate the TS client
	uv run python -m handball_api.openapi packages/api-client/openapi.json
	pnpm --filter @handball/api-client generate

policy-doc: ## Regenerate docs/policy-matrix.md from the policy table
	uv run python -c "from handball_api.services.policies import matrix_markdown; print(matrix_markdown(), end='')" > docs/policy-matrix.md

lint: ## Lint Python and TS, check formatting, import contracts, circular deps
	uv run ruff check .
	uv run ruff format --check .
	uv run lint-imports
	pnpm lint
	pnpm circular

fmt: ## Auto-format
	uv run ruff check --fix .
	uv run ruff format .
	pnpm format

typecheck: typecheck-py ## mypy strict + tsc strict
	pnpm typecheck

typecheck-py:
	uv run mypy $(PY_SRC) $(PY_TESTS)

test: test-py test-js ## Run all unit tests (no running services needed)

db: ## Start only Postgres (needed by the API tests)
	docker compose up -d --wait postgres

test-py: db ## Python tests with coverage gate (80 %), needs Postgres
	uv run python packages/court/scripts/generate.py --check
	uv run python packages/plans/generate.py --check
	uv run python apps/site/scripts/make_demo.py --check
	uv run pytest apps packages --cov --cov-report=term

test-js: ## Vitest
	pnpm test

test-integration: ## Tests against the running compose stack (make up first)
	uv run pytest apps packages -m integration

test-e2e: ## Playwright against http://localhost:3000 (make up first)
	pnpm --filter @handball/web test:e2e

migrate: ## Apply DB migrations inside the stack
	docker compose run --rm migrate

plans: ## Plan catalogue for the marketing site (packages/plans/plans.json)
	uv run python packages/plans/generate.py
	uv run python apps/site/scripts/make_demo.py

migration: ## Create a migration: make migration m="add teams"
	cd apps/api && uv run alembic revision --autogenerate -m "$(m)"

seed: ## Demo club, teams, matches and synthetic videos (stack must be running)
	uv run python scripts/seed.py

eval: ## Evaluation harness on the synthetic golden set (writes docs/perf/eval.md)
	uv run python ml/eval/run.py --seconds 60 --out docs/perf/eval.md

eval-real: ## Health checks on the real test videos in data/videos/ (writes docs/perf/eval-real.md)
	uv run python ml/eval/real.py --out docs/perf/eval-real.md

testdata: ## Download the shared real test videos to data/videos/ (needs TESTDATA_S3_* env, see data/README.md)
	uv run python scripts/testdata.py pull

testdata-push: ## Upload a real test video: make testdata-push f=match.mp4 id=2026-10-12-u17-home
	uv run python scripts/testdata.py push "$(f)" --id "$(id)"

bench: ## Per-stage timing of the analysis pipeline
	uv run python ml/eval/bench.py

check: lint typecheck test ## Everything CI runs without services

.PHONY: plans eval eval-real testdata testdata-push bench help install up down logs court api-client lint fmt typecheck typecheck-py db policy-doc test test-py test-js test-integration test-e2e migrate migration seed check

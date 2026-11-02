SHELL := /bin/bash
.DEFAULT_GOAL := help
PY_SRC := apps/api/src apps/worker/src apps/gpu-worker/src packages/court/handball_court
PY_TESTS := apps/api/tests apps/worker/tests apps/gpu-worker/tests packages/court/tests

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

test-py: ## Python tests with coverage gate (80 %)
	uv run python packages/court/scripts/generate.py --check
	uv run pytest apps packages --cov --cov-report=term

test-js: ## Vitest
	pnpm test

test-integration: ## Tests against the running compose stack (make up first)
	uv run pytest apps packages -m integration

test-e2e: ## Playwright against http://localhost:3000 (make up first)
	pnpm --filter @handball/web test:e2e

migrate: ## Apply DB migrations inside the stack
	docker compose run --rm migrate

migration: ## Create a migration: make migration m="add teams"
	cd apps/api && uv run alembic revision --autogenerate -m "$(m)"

seed: ## Demo data (from M1 on)
	@echo "make seed: demo data generator arrives with M1/M2 (see docs/PLAN.md)"; exit 1

check: lint typecheck test ## Everything CI runs without services

.PHONY: help install up down logs court api-client lint fmt typecheck typecheck-py test test-py test-js test-integration test-e2e migrate migration seed check

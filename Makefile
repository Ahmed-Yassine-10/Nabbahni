# ─────────────────────────────────────────────────────────────
# SentinelleRx — developer task runner
# On Windows, run these via Git Bash / WSL, or use the PowerShell
# equivalents documented in README.md.
# ─────────────────────────────────────────────────────────────
.DEFAULT_GOAL := help
.PHONY: help up down logs ps seed train score api worker web \
        migrate revision test test-backend test-ml lint fmt \
        openapi demo clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-14s\033[0m %s\n", $$1, $$2}'

## ---- Infrastructure ----
up: ## Start all infrastructure containers
	docker compose up -d
	@echo "Waiting for services to become healthy..."
	docker compose ps

down: ## Stop all containers
	docker compose down

logs: ## Tail container logs
	docker compose logs -f --tail=100

ps: ## Show container status
	docker compose ps

## ---- Backend / DB ----
migrate: ## Apply Alembic migrations
	cd backend && alembic upgrade head

revision: ## Create a new Alembic autogenerate revision (msg=...)
	cd backend && alembic revision --autogenerate -m "$(msg)"

api: ## Run the FastAPI server (dev, reload)
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

worker: ## Run the RabbitMQ alert worker
	cd backend && python -m app.workers.alert_worker

openapi: ## Export OpenAPI spec to docs/api/openapi.json
	cd backend && python -m app.tools.export_openapi

## ---- Data + ML ----
seed: ## Generate + load synthetic Tunisian dataset
	cd data-generator && python -m generator.seed --seed 42

train: ## Train demand + shortage models and register champions
	cd ml && python -m ml.train_all

score: ## Run batch scoring -> writes predictions/recommendations/alerts
	cd ml && python -m ml.score

## ---- Frontend ----
web: ## Run the Next.js dev server
	cd frontend && npm run dev

## ---- Quality ----
test: test-backend test-ml ## Run all Python tests

test-backend: ## Run backend tests
	cd backend && pytest -q

test-ml: ## Run ml tests
	cd ml && pytest -q

lint: ## Lint Python code
	ruff check backend ml data-generator

fmt: ## Format Python code
	ruff format backend ml data-generator

## ---- End to end ----
demo: ## Full pipeline: migrate -> seed -> train -> score
	$(MAKE) migrate && $(MAKE) seed && $(MAKE) train && $(MAKE) score
	@echo "Demo data ready. Start the API (make api) and web (make web)."

clean: ## Remove containers + volumes (DESTRUCTIVE)
	docker compose down -v

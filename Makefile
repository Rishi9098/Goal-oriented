# Northstar — development commands.
#
# Native (no containers) is the default workflow — see scripts/setup_mac.sh
# / setup_linux.sh / setup_windows.ps1. Container targets below are for
# testing the production image locally, not for day-to-day development.

.DEFAULT_GOAL := help

UNAME := $(shell uname -s)

.PHONY: help setup dev migrate test lint seed reset-db \
        container-build container-run docker-build docker-up clean

help: ## Show this help
	@echo "Northstar — available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

setup: ## Native setup — detects macOS/Linux and runs the matching script (Windows: pwsh scripts/setup_windows.ps1)
ifeq ($(UNAME),Darwin)
	@./scripts/setup_mac.sh
else ifeq ($(UNAME),Linux)
	@./scripts/setup_linux.sh
else
	@echo "Unsupported OS for 'make setup'. On Windows, run: pwsh scripts/setup_windows.ps1"; exit 1
endif

dev: ## Run backend + frontend together (Ctrl+C stops both)
	@./scripts/dev.sh

migrate: ## Run Alembic migrations — upgrade head by default, or make migrate ARGS="downgrade -1"
	@./scripts/migrate.sh $(ARGS)

test: ## Run backend + frontend test/verify suites — extra pytest args via ARGS
	@./scripts/test.sh $(ARGS)

lint: ## Run backend + frontend lint/type checks
	@./scripts/lint.sh

seed: ## Seed local dev DB with a demo user + sample goals (idempotent)
	@./scripts/seed.sh

reset-db: ## Drop + recreate the local dev DB, then migrate — make reset-db ARGS=--yes to skip the prompt
	@./scripts/reset_db.sh $(ARGS)

container-build: ## Build the production image with Apple's `container` CLI (macOS 26+, Apple Silicon)
	@container build -t northstar-backend:local ./backend

container-run: ## Run the production image with Apple's `container` CLI
	@container run --rm -it -p 8000:8000 --env-file backend/.env northstar-backend:local

docker-build: ## Build the production image with Docker/OCI (CI + production path)
	@docker build -t northstar-backend:local ./backend

docker-up: ## Run the full stack via docker compose (CI/prod parity — not required for daily dev)
	@docker compose up --build

clean: ## Remove local venv/node_modules/build artifacts (does not touch the database)
	@rm -rf backend/.venv backend/.pytest_cache backend/htmlcov \
		code/node_modules code/.output code/.wrangler code/.tanstack/tmp
	@echo "Cleaned. Run 'make setup' to rebuild."

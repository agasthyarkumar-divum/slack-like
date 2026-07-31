# Divum Chat — convenience targets for local development.
# Run `make help` (or just `make`) to list everything.

SHELL := /bin/bash
BACKEND_DIR := backend
MOBILE_DIR := mobile
VENV := $(BACKEND_DIR)/.venv

.DEFAULT_GOAL := help

.PHONY: help \
	env \
	up down restart logs ps rebuild \
	venv backend-dev migrate migration db-shell test \
	mobile-install mobile mobile-web mobile-android mobile-ios typecheck \
	clean-ports clean

help: ## Show this list of targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

## --- One-time setup ---

env: ## Copy .env.example -> .env if .env doesn't exist yet
	@[ -f .env ] || (cp .env.example .env && echo "Created .env — edit it before deploying anywhere but localhost.")

## --- Backend (Docker Compose: postgres, redis, api, worker) ---

up: env ## Build and start the full backend stack in the background
	docker-compose up -d --build

down: ## Stop the backend stack (keeps volumes: db data, uploads)
	docker-compose down

restart: ## Restart the api and worker containers (e.g. after a dependency change)
	docker-compose up -d --build api worker

logs: ## Tail API logs (Ctrl+C to stop tailing, containers keep running)
	docker-compose logs -f api

ps: ## Show status of backend containers
	docker-compose ps

rebuild: ## Rebuild images from scratch, no layer cache
	docker-compose build --no-cache

## --- Backend (host dev: run uvicorn directly, e.g. to attach a debugger) ---
## NOTE: stops the containerized `api` first so it doesn't fight over port 8000
## for host port 8000 — db/redis stay in Docker.

venv: ## Create backend/.venv and install Python dependencies
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install --quiet --upgrade pip
	$(VENV)/bin/pip install --quiet -r $(BACKEND_DIR)/requirements.txt

backend-dev: venv ## Run the API on the host with --reload (db/redis via Docker, api container stopped)
	docker-compose up -d db redis
	docker-compose stop api 2>/dev/null || true
	[ -f $(BACKEND_DIR)/.env ] || cp $(BACKEND_DIR)/.env.example $(BACKEND_DIR)/.env
	cd $(BACKEND_DIR) && source .venv/bin/activate && uvicorn app.main:app --reload

migrate: venv ## Apply Alembic migrations (upgrade head)
	docker-compose up -d db
	cd $(BACKEND_DIR) && source .venv/bin/activate && alembic upgrade head

migration: venv ## Autogenerate a new migration: make migration m="add users table"
	docker-compose up -d db
	cd $(BACKEND_DIR) && source .venv/bin/activate && alembic revision --autogenerate -m "$(m)"

db-shell: ## Open a psql shell against the running db container
	docker-compose exec db psql -U $${POSTGRES_USER:-company_chat} -d $${POSTGRES_DB:-company_chat}

test: venv ## Run the backend test suite (needs a real Postgres — creates a *_test db on the `db` container)
	$(VENV)/bin/pip install --quiet -r $(BACKEND_DIR)/requirements-dev.txt
	docker-compose up -d db
	cd $(BACKEND_DIR) && source .venv/bin/activate && pytest

## --- Mobile (Expo) ---

mobile-install: ## Install mobile dependencies
	cd $(MOBILE_DIR) && npm install

mobile: mobile-install ## Start the Expo dev server (scan QR with Expo Go, or press i/a/w)
	cd $(MOBILE_DIR) && npx expo start

mobile-web: mobile-install ## Start Expo and open the web preview directly
	cd $(MOBILE_DIR) && npx expo start --web

mobile-android: mobile-install ## Start Expo targeting an Android emulator/device
	cd $(MOBILE_DIR) && npx expo start --android

mobile-ios: mobile-install ## Start Expo targeting an iOS simulator/device
	cd $(MOBILE_DIR) && npx expo start --ios

typecheck: ## Type-check the mobile app
	cd $(MOBILE_DIR) && npx tsc --noEmit

## --- Cleanup ---

clean-ports: ## Kill any stray Metro/Expo dev servers left listening on 8081/8082/19000-19002
	@for p in 8081 8082 19000 19001 19002; do \
		pid=$$(lsof -ti:$$p -sTCP:LISTEN 2>/dev/null); \
		if [ -n "$$pid" ]; then echo "killing pid $$pid on port $$p"; kill $$pid; fi; \
	done

clean: down ## Stop containers AND remove their volumes (deletes local db data + uploads)
	docker-compose down -v

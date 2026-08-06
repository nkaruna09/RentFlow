# Developer shortcuts. TODO: verify each target once the services run.

.PHONY: help up down logs migrate revision seed lint test fmt

help:
	@echo "up        start the local stack"
	@echo "down      stop the stack and remove the db volume"
	@echo "logs      tail all service logs"
	@echo "migrate   apply database migrations"
	@echo "revision  autogenerate a migration (m=\"message\")"
	@echo "seed      load demo data"
	@echo "lint      run linters for both apps"
	@echo "test      run tests for both apps"
	@echo "fmt       format both apps"

up:
	docker compose up --build

down:
	docker compose down -v

logs:
	docker compose logs -f

migrate:
	docker compose exec api alembic upgrade head

revision:
	docker compose exec api alembic revision --autogenerate -m "$(m)"

seed:
	docker compose exec api python -m scripts.seed

lint:
	cd backend && ruff check . && mypy app
	cd frontend && npm run lint && npm run typecheck

test:
	cd backend && pytest
	cd frontend && npm run test

fmt:
	cd backend && ruff format .
	cd frontend && npm run format

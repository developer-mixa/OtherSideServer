.PHONY: install dev test test-unit lint fmt audit check migrate upgrade \
	docker-up docker-up-production docker-down docker-logs

install:
	pip install -e ".[dev]"

dev:
	uvicorn main:app --reload --app-dir src

# Full suite. Integration tests start PostgreSQL in Docker via testcontainers
# (or use TEST_DATABASE_URL=postgresql+asyncpg://... to point at a running server).
test:
	pytest -q --cov=src --cov-report=term-missing

# Fast feedback: domain/application/unit tests only, no Docker needed.
test-unit:
	pytest -q -m "not integration"

lint:
	ruff check src tests
	ruff format --check src tests
	mypy src

fmt:
	ruff format src tests
	ruff check --fix src tests

# Known vulnerabilities in installed dependencies (the project itself is not on PyPI).
audit:
	pip-audit --skip-editable

# Everything CI runs, minus the Docker image build.
check: lint test audit

migrate:
	alembic revision --autogenerate -m "$(msg)"

upgrade:
	alembic upgrade head

docker-up-production:
	docker compose up -d --build

docker-up:
	docker compose up

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f api

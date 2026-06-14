.PHONY: dev test lint fmt migrate upgrade docker-up docker-down

dev:
	uvicorn main:app --reload --app-dir src

test:
	pytest -q --cov=src --cov-report=term-missing

lint:
	ruff check src tests
	mypy src

fmt:
	ruff format src tests
	ruff check --fix src tests

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

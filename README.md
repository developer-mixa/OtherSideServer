# OtherSide API

Production-ready FastAPI backend with Clean Architecture, PostgreSQL, JWT auth, and Docker deployment.

> Backend lives in `OtherSideServer/`. All commands below run from that directory.

## Architecture

```
src/
├── domain/          # Entities, value objects, domain services, exceptions
├── application/     # Use cases, DTOs, interfaces, Unit of Work
├── presentation/    # API routers, Pydantic schemas, exception handlers
├── infrastructure/  # SQLAlchemy models, repositories, Alembic
└── config/          # Settings, DI (dishka), security, logging
```

Dependency rule: **Infrastructure → Presentation → Application → Domain**

## Quick Start

### Docker (recommended)

```bash
cd OtherSideServer
cp .env.example .env
make docker-up
```

API available at: http://localhost:8000

- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc
- Health check: http://localhost:8000/health

### Local development

```bash
cd OtherSideServer
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Start PostgreSQL (or use docker compose db only)
docker compose up -d db

cp .env.example .env
# Set DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/app

make upgrade   # run Alembic migrations
make dev       # start uvicorn with hot reload
```

## Makefile Commands

| Command | Description |
|---------|-------------|
| `make dev` | Start dev server with hot reload |
| `make test` | Run pytest with coverage (>80%) |
| `make lint` | Run ruff + mypy |
| `make fmt` | Format code with ruff |
| `make migrate msg="Desc"` | Create Alembic migration |
| `make upgrade` | Apply migrations |
| `make docker-up` | Build and start all services |
| `make docker-down` | Stop services |

## API Endpoints (`/api/v1`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/register` | No | Register user |
| POST | `/auth/login` | No | Get JWT token |
| GET | `/auth/me` | Yes | Current user |
| GET/POST | `/roles` | No | List/create roles |
| GET/POST/DELETE | `/games` | No | Company games CRUD |
| GET/POST | `/plans` | No | Subscription plans |
| GET/POST | `/subscriptions` | No | User subscriptions |
| GET/POST | `/promocodes` | No | Promocodes |
| GET | `/payments/me` | Yes | User payments |
| `POST` | `/payments/init` | Yes | Initiate Robokassa payment |
| `GET` | `/payments/{id}` | Yes | Payment status |
| `POST` | `/payments/robokassa/result` | No | Robokassa webhook |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | OtherSide API | Application title |
| `ENV` | local | Environment name |
| `DEBUG` | true | Debug mode |
| `SECRET_KEY` | change-me | JWT signing key (**change in production**) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 60 | JWT TTL |
| `JWT_ALG` | HS256 | JWT algorithm |
| `DATABASE_URL` | — | Async PostgreSQL URL (`postgresql+asyncpg://...`) |
| `CORS_ORIGINS` | `["*"]` | Allowed CORS origins |
| `ROBOKASSA_MERCHANT_LOGIN` | — | Robokassa merchant login |
| `ROBOKASSA_PASSWORD1` | — | Password #1 (payment URL signature) |
| `ROBOKASSA_PASSWORD2` | — | Password #2 (Result URL verification) |
| `ROBOKASSA_IS_TEST` | true | Test mode flag |
| `ROBOKASSA_PAYMENT_URL` | auth.robokassa.ru | Payment page base URL |

## Database Schema

Source of truth: `db/schema/InitTables.sql`

Tables: `roles`, `users`, `company_games`, `subscription_plans`, `subscriptions`, `promocodes`, `payments`, `payment_events`

## Testing

```bash
make test
```

Tests use in-memory fake UoW for API/application layers and mapper round-trip tests for infrastructure.

## Pre-commit

```bash
pip install pre-commit
pre-commit install
```

Runs ruff (lint + format) and mypy on each commit.

## Production deployment

Полная инструкция для Selectel (VPS + Nginx + SSL): [../DEPLOY-SELECTEL.md](../DEPLOY-SELECTEL.md)

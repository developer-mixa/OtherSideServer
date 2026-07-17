# OtherSide API

Production-ready FastAPI backend with Clean Architecture, PostgreSQL, JWT auth, and Docker deployment.

> Backend lives in `OtherSideServer/`. All commands below run from that directory.

## Contents

- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Makefile Commands](#makefile-commands)
- [API Endpoints](#api-endpoints-apiv1)
- [First admin setup](#first-admin-setup)
  - [Promoting an additional user to admin](#promoting-an-additional-user-to-admin)
- [Environment Variables](#environment-variables)
- [Robokassa merchant setup](#robokassa-merchant-setup)
- [Database Schema](#database-schema)
- [Testing](#testing)
- [Pre-commit](#pre-commit)
- [Production deployment](#production-deployment)

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
| GET/POST | `/roles` | Admin | List/create roles |
| GET/POST/DELETE | `/games` | Admin | Company games CRUD |
| GET | `/plans` | No | List subscription plans |
| POST | `/plans` | Admin | Create subscription plans |
| GET | `/subscriptions` | Yes | Own subscriptions (admin: all or filter by user) |
| POST | `/subscriptions` | Admin | Manual subscription grant |
| GET/POST | `/promocodes` | Admin | Promocodes |
| GET | `/payments/me` | Yes | User payments |
| `POST` | `/payments/init` | Yes | Initiate Robokassa payment |
| `GET` | `/payments/{id}` | Yes | Payment status |
| `POST` | `/payments/robokassa/result` | No | Robokassa webhook |
| GET/PATCH | `/settings/maintenance` | PATCH: admin | Maintenance mode |
| POST | `/contact/submissions` | No | Submit contact form |
| GET | `/contact/submissions` | Admin | List contact submissions |
| GET | `/landing/public` | No | Countdown + roadmap for landing |
| GET/PATCH | `/landing/settings` | Admin | Countdown title & release date |
| GET/POST/PATCH/DELETE | `/landing/tasks` | Admin | Roadmap graph tasks |

## First admin setup

Public registration **always** creates a `user` role account. Admin access is granted only via the `admin` role in the database.

1. Run migrations (seeds `user` and `admin` roles):

```bash
make upgrade
```

2. Configure bootstrap credentials in `.env` (minimum 12 characters for password):

```env
BOOTSTRAP_ADMIN_USERNAME=admin
BOOTSTRAP_ADMIN_EMAIL=admin@example.com
BOOTSTRAP_ADMIN_PASSWORD=your-secure-password-here
```

3. Start the API. On the **first startup**, if no admin user exists yet, one is created automatically from these variables.

4. Log in at `POST /api/v1/auth/login` and open `/admin` in the frontend.

5. After the admin exists, you may remove `BOOTSTRAP_ADMIN_*` from `.env` (optional, recommended for production). Subsequent startups will skip bootstrap.

`GET /api/v1/auth/me` returns `"is_admin": true` for admin users — the frontend uses this flag (no role UUID in env required).

### Promoting an additional user to admin

`BOOTSTRAP_ADMIN_*` only creates **one** admin, once, on first startup. There is no API
endpoint to promote a user afterward — do it directly in the database:

```bash
docker compose -f docker-compose.prod.yml exec db psql -U postgres -d app -c \
  "UPDATE users SET role_id = (SELECT id FROM roles WHERE role = 'admin') WHERE email = 'someone@example.com';"
```

No re-login needed — the JWT only carries the user id, `/auth/me` resolves `is_admin` from the
DB on every call, so the existing token picks up the new role immediately. The frontend may
still need a page refresh to refetch `/auth/me` and show the admin UI.

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
| `BOOTSTRAP_ADMIN_USERNAME` | — | Initial admin username (first startup only) |
| `BOOTSTRAP_ADMIN_EMAIL` | — | Initial admin email |
| `BOOTSTRAP_ADMIN_PASSWORD` | — | Initial admin password (min 12 chars) |

## Robokassa merchant setup

In the Robokassa merchant panel (Технические настройки), set:

| Field | Value |
|-------|-------|
| Result URL | `https://api.otherside-inc.ru/api/v1/payments/robokassa/result` |
| Result URL method | GET or POST — both are supported (`payments.robokassa_result`) |
| Success URL | `https://otherside-inc.ru/payments/success` |
| Fail URL | `https://otherside-inc.ru/payments/fail` |

Result URL is the authoritative server-to-server callback: it verifies the Password #2 signature
and fulfills the payment (`ProcessRobokassaWebhookUseCase`). Success/Fail URLs are browser
redirects only — pure confirmation pages in the frontend (`OtherSideFrontend/src/app/(public)/payments`)
with no bearing on whether the subscription is actually granted.

## Database Schema

Source of truth: `db/schema/InitTables.sql`

Tables: `roles`, `users`, `company_games`, `subscription_plans`, `subscriptions`, `promocodes`, `payments`, `payment_events`, `system_settings`, `contact_submissions`, `landing_settings`, `roadmap_tasks`

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

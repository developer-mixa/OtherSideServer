# OtherSide API — CLAUDE.md

FastAPI backend, Clean Architecture, PostgreSQL + SQLAlchemy async, JWT auth, dishka DI.

**Production domain:** `https://otherside-inc.ru` (site) / `https://api.otherside-inc.ru` (API).
Robokassa merchant tech settings (`Result URL` / `Success URL` / `Fail URL`) must point at these
hosts — see `src/presentation/api/v1/endpoints/payments.py` for the Result URL webhook and
`OtherSideFrontend/src/app/(public)/payments/{success,fail}` for the redirect pages.

## Architecture (strict dependency rule)

```
src/
├── domain/          # Entities, value objects, domain services, exceptions — no framework imports
├── application/     # Use cases, DTOs, interfaces (ports), Unit of Work — orchestrates domain
├── infrastructure/  # SQLAlchemy models, repositories, mappers, external clients (Robokassa, cache)
├── presentation/    # FastAPI routers, Pydantic schemas, exception handlers — thin, no business logic
└── config/          # Settings, dishka providers, security (JWT/hashing), logging
```

**Dependency direction:** `infrastructure → presentation → application → domain`.
Domain never imports from application/infrastructure/presentation. Use cases depend on
`application/interfaces` (ports), never on concrete SQLAlchemy/HTTP classes directly.

## Non-negotiable rules

- **Async everywhere for I/O.** No blocking calls in async functions (DB, HTTP, file I/O).
- **DI via dishka only.** Every external dependency (session, repo, client) is injected — never
  instantiated inline in a use case or endpoint. This is what makes use cases unit-testable.
- **Unit of Work** wraps all multi-repository DB operations; commit/rollback lives in the UoW,
  not scattered across use cases.
- **Business logic lives in `application/use_cases`**, never in `presentation` endpoints. Endpoints
  only: parse request → call use case → map result to schema.
- **Domain entities ≠ persistence models.** Map between `domain/entities` and
  `infrastructure/db/models` explicitly via `infrastructure/mappers`.
- **Full type hints**, `mypy --strict` must pass. Avoid `Any` without a comment explaining why.
- **Pydantic v2** for all schemas/DTOs.
- **No bare `except Exception: pass`.** Catch specific exceptions, log, re-raise as domain/HTTP
  exceptions as appropriate.
- **No secrets in code.** Everything sensitive comes from `config.settings` (env-backed).
- **Small, linear, reversible Alembic migrations** — one logical change per migration.

## Testing

- Unit tests (`tests/test_domain`, `tests/test_application`): no real DB, use the in-memory fake
  UoW/repos pattern already in `tests/conftest.py`.
- Integration tests: real PostgreSQL 16 via testcontainers (`database_url` session fixture, or
  `TEST_DATABASE_URL`), schema built by Alembic migrations. Use `pg_uow`/`db_session` (rolled
  back after each test) or `committing_session_factory` (multi-connection tests; clean up
  yourself). Tests depending on the DB are auto-marked `integration`. No SQLite.
- API tests (`tests/test_presentation`): `httpx.AsyncClient` against `main.create_app()`; they
  need the DB because `MaintenanceMiddleware` reads it directly.
- Coverage gate is `[tool.coverage.report] fail_under` in pyproject (ratchet: raise, never
  lower). Every new use case needs at least one unit test; every new endpoint needs at least
  one API test; every migration must downgrade cleanly (`tests/test_migrations.py`).
- Run: `make test-unit` (fast), `make test` (full + coverage), `make lint` (ruff + format +
  mypy) before considering work done. CI (`.github/workflows/ci.yml`) runs the same.
- Password hashing goes through `PasswordHasherProtocol` (never hash inline in a use case).
- Authenticated endpoints resolve the caller with
  `await authenticate.execute(bearer_token(credentials))` (`AuthenticateAccessTokenUseCase`
  via dishka) — it also rejects access tokens of revoked sessions. Never decode the JWT alone.
- Architectural decisions are recorded in `docs/adr/`.

## Commands

```bash
make dev        # uvicorn --reload
make test       # full suite + coverage (Docker for testcontainers)
make test-unit  # fast tests, no Docker
make lint       # ruff check + ruff format --check + mypy
make audit      # pip-audit
make fmt        # ruff format + ruff check --fix
make migrate msg="add X"   # alembic revision --autogenerate
make upgrade    # alembic upgrade head
```

## When adding a feature

1. Domain entity/value object first (if new concept).
2. Use case in `application/use_cases` + DTO, depending only on interfaces.
3. Repository interface in `application/interfaces`, implementation in `infrastructure/db/repositories`.
4. Wire it in `config/ioc` (dishka provider).
5. Presentation router + Pydantic schema, thin, delegates to the use case.
6. Alembic migration if the schema changed.
7. Tests: unit for the use case, API test for the endpoint.

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
- [Настройка email-верификации (Selectel)](#настройка-email-верификации-selectel)
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
| POST | `/auth/register` | No | Register user, sends email verification code |
| POST | `/auth/verify-email` | No | Confirm email with the 6-digit code |
| POST | `/auth/resend-verification` | No | Send a new verification code |
| POST | `/auth/login` | No | Get JWT token (requires verified email) |
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
| `SMTP_HOST` | — | SMTP relay host (Selectel: `smtp.mail.selcloud.ru`) |
| `SMTP_PORT` | 1127 | SMTP port (Selectel: 1127 = TLS/SSL, 1126 = no SSL) |
| `SMTP_USERNAME` | — | SMTP login |
| `SMTP_PASSWORD` | — | SMTP password |
| `SMTP_FROM_EMAIL` | — | Sender address (must be on a domain verified with the SMTP provider) |
| `SMTP_FROM_NAME` | OtherSide | Sender display name |
| `SMTP_USE_TLS` | true | Use TLS/SSL for the SMTP connection |
| `EMAIL_VERIFICATION_CODE_TTL_MINUTES` | 15 | How long a verification code stays valid |
| `EMAIL_VERIFICATION_MAX_ATTEMPTS` | 5 | Wrong-code attempts allowed before a new code is required |

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

## Настройка email-верификации (Selectel)

При регистрации (`POST /auth/register`) на почту пользователя отправляется 6-значный код
подтверждения (действует `EMAIL_VERIFICATION_CODE_TTL_MINUTES` минут, по умолчанию 15). Пока
email не подтверждён кодом через `POST /auth/verify-email`, `POST /auth/login` возвращает
`403 {"code": "email_not_verified"}`. Если код не пришёл или устарел — `POST
/auth/resend-verification` присылает новый.

Отправка писем идёт по обычному SMTP (`src/infrastructure/email/smtp_client.py`), поэтому подойдёт
любой SMTP-провайдер — но по умолчанию всё настроено под **почтовый сервис Selectel** (SMTP-relay
для транзакционных писем). Настройка целиком — на стороне Selectel и в `.env`, кода менять не
нужно.

### 1. Создать ресурс в панели Selectel

1. Панель управления Selectel → **Продукты → Почтовый сервис** → «Создать ресурс».
2. Задайте имя ресурса — это просто ярлык внутри панели, на настройки не влияет.

### 2. Подтвердить домен

1. На вкладке **Информация** ресурса скопируйте «Ключ для подтверждения владения доменом».
2. У вашего DNS-регистратора (там, где управляется `otherside-inc.ru` или другой домен, с которого
   будут отправляться письма) добавьте TXT-запись:
   - Тип: `TXT`
   - Имя: сам домен (например, `otherside-inc.ru`)
   - Значение: скопированный ключ
3. В той же вкладке нажмите «Добавить» под «Привязанные домены» и укажите домен. К одному ресурсу
   можно привязать до трёх доменов.

### 3. Добавить DNS-записи DKIM / DMARC / SPF

После привязки домена в панели появятся готовые значения — добавьте их у регистратора:

| Тип | Имя | Значение |
|-----|-----|----------|
| TXT (DKIM) | `selcloud._domainkey.<ваш-домен>` | значение из карточки домена в панели (строка DKIM) |
| TXT (DMARC) | `_dmarc.<ваш-домен>` | `v=DMARC1; p=quarantine;` |
| TXT (SPF) | `<ваш-домен>` | `v=spf1 include:spf.mail.selcloud.ru ?all` (если SPF-запись уже есть — просто добавьте `include:spf.mail.selcloud.ru` в неё, второй TXT-записи с `v=spf1` на домене быть не должно) |

DNS может обновляться до 72 часов — до этого письма могут попадать в спам или не отправляться.

### 4. Получить SMTP-логин/пароль

На вкладке **Информация** ресурса — данные для подключения:

- Хост: `smtp.mail.selcloud.ru`
- Порт: `1127` (TLS/SSL, рекомендуется) или `1126` (без шифрования)
- Логин и пароль — там же, в карточке ресурса

### 5. Прописать переменные в `.env`

```env
SMTP_HOST=smtp.mail.selcloud.ru
SMTP_PORT=1127
SMTP_USERNAME=<логин из панели Selectel>
SMTP_PASSWORD=<пароль из панели Selectel>
SMTP_FROM_EMAIL=noreply@<ваш-домен>   # адрес должен быть на подтверждённом домене
SMTP_FROM_NAME=OtherSide
SMTP_USE_TLS=true
```

`SMTP_FROM_EMAIL` не обязан существовать как настоящий почтовый ящик — важно только, чтобы его
домен совпадал с доменом, подтверждённым в шагах 2-3.

### 6. Перезапустить бэкенд

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

В production-режиме (`ENV=production`) приложение **не запустится**, если `SMTP_HOST`,
`SMTP_USERNAME`, `SMTP_PASSWORD` или `SMTP_FROM_EMAIL` не заданы — это защита от повторения
ситуации, когда сломанная интеграция роняет запросы уже после того, как они попали в прод (как
было с 500-ошибкой при регистрации до этого фикса).

### Проверка

Зарегистрируйте тестового пользователя через `/auth/register` и убедитесь, что письмо с кодом
пришло на почту. Если письмо не приходит — смотри логи API (`docker compose -f
docker-compose.prod.yml logs -f api`): ошибки SMTP логируются как `Failed to send verification
email to ...` и не приводят к 500 — сам аккаунт при этом уже создан, просто письмо не ушло
(пользователь может запросить код повторно через `/auth/resend-verification`, когда SMTP заработает).

## Database Schema

Source of truth: Alembic migrations (`migrations/versions/`). `alembic upgrade head` builds the
full schema from an empty database — there is no separate SQL init script.

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

# Деплой OtherSide на Selectel (VPS + Nginx)

Полная инструкция: один VPS в Selectel, фронтенд + бэкенд + PostgreSQL в Docker, Nginx как reverse proxy, бесплатный SSL (Let's Encrypt).

> Замени `otherside.ru` на свой домен во всех конфигах.  
> API: `api.otherside.ru` · Сайт: `otherside.ru` и `www.otherside.ru`

## Схема

```
Интернет
   │
   ├─ otherside.ru      ──► Nginx :443 ──► Next.js :3000 (Docker)
   ├─ www.otherside.ru  ──►     "
   └─ api.otherside.ru  ──► Nginx :443 ──► FastAPI :8000 (Docker)
                                      └──► PostgreSQL (только внутри Docker)
```

---

## Часть 1. Selectel: сервер и DNS

### 1.1 Создай облачный сервер

Панель Selectel → **Облачные серверы** → **Создать сервер**:

| Параметр | Рекомендация |
|----------|----------------|
| ОС | Ubuntu 22.04 или 24.04 LTS |
| CPU/RAM | минимум 2 vCPU / 2–4 GB RAM |
| Диск | 20–40 GB SSD |
| Публичный IP | **Включить** (floating/public) |

Запиши **публичный IP** сервера — например `185.x.x.x`.

### 1.2 DNS в Selectel

**Панель Selectel → DNS** (или DNS у регистратора, если домен не в Selectel).

Добавь записи:

| Тип | Имя (host) | Значение | TTL |
|-----|------------|----------|-----|
| `A` | `@` | `185.x.x.x` | 300 |
| `A` | `www` | `185.x.x.x` | 300 |
| `A` | `api` | `185.x.x.x` | 300 |

Подожди 5–30 минут, проверь:

```bash
dig otherside.ru +short
dig api.otherside.ru +short
```

Оба должны вернуть IP сервера.

### 1.3 Firewall в Selectel

В security groups / firewall разреши входящие:

- `22` (SSH)
- `80` (HTTP — для certbot)
- `443` (HTTPS)

**Не открывай** наружу `8000`, `3000`, `5432` — к ним ходит только Nginx на localhost.

---

## Часть 2. Подготовка сервера

Подключись по SSH:

```bash
ssh root@185.x.x.x
```

### 2.1 Базовые пакеты

```bash
apt update && apt upgrade -y
apt install -y git curl ufw nginx certbot python3-certbot-nginx
```

### 2.2 Firewall (ufw)

```bash
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw enable
ufw status
```

### 2.3 Docker

```bash
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker
apt install -y docker-compose-plugin
docker --version
docker compose version
```

### 2.4 Пользователь для деплоя (опционально)

```bash
adduser deploy
usermod -aG docker deploy
usermod -aG sudo deploy
```

### 2.5 Каталог проекта

```bash
mkdir -p /opt/otherside
cd /opt/otherside
```

Залей код на сервер:

```bash
# Вариант A — git
git clone <твой-репозиторий-backend> OtherSideServer
git clone <твой-репозиторий-frontend> OtherSideFrontend

# Вариант B — rsync с локальной машины
# rsync -avz --exclude node_modules --exclude .next \
#   /path/to/OtherSideServer/ deploy@185.x.x.x:/opt/otherside/OtherSideServer/
# rsync -avz --exclude node_modules --exclude .next \
#   /path/to/OtherSideFrontend/ deploy@185.x.x.x:/opt/otherside/OtherSideFrontend/
```

Структура на сервере:

```
/opt/otherside/
├── OtherSideServer/
└── OtherSideFrontend/
```

---

## Часть 3. Бэкенд (OtherSideServer)

Текущий `docker-compose.yml` в репозитории — **для разработки** (`--reload`, открытый порт БД).  
На сервере создай **`OtherSideServer/docker-compose.prod.yml`**:

```yaml
services:
  api:
    build: .
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy
    env_file:
      - .env
    ports:
      - "127.0.0.1:8000:8000"
    command: uvicorn main:app --host 0.0.0.0 --port 8000

  db:
    image: postgres:16
    restart: unless-stopped
    environment:
      POSTGRES_DB: app
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d app"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  pgdata:
```

### 3.1 `.env` для production

```bash
cd /opt/otherside/OtherSideServer
cp .env.example .env
nano .env
```

Содержимое:

```env
APP_NAME=OtherSide API
ENV=production
DEBUG=false

SECRET_KEY=<сгенерируй: openssl rand -hex 32>
ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_ALG=HS256

DATABASE_URL=postgresql+asyncpg://postgres:<ПАРОЛЬ_БД>@db:5432/app
CORS_ORIGINS=["https://otherside.ru","https://www.otherside.ru"]

POSTGRES_PASSWORD=<сильный-пароль-бд>
```

`DATABASE_URL` и `POSTGRES_PASSWORD` должны использовать один и тот же пароль.

Помимо этого заполни в `.env` (полный список переменных и их описание — в `.env.example`):
- `ROBOKASSA_*` — данные мерчанта Robokassa;
- `SMTP_*` — доступ к почтовому сервису для отправки кода подтверждения email при регистрации.
  В production-режиме (`ENV=production`) сервер откажется стартовать, если `SMTP_HOST`,
  `SMTP_USERNAME`, `SMTP_PASSWORD` или `SMTP_FROM_EMAIL` не заданы. Полная инструкция по
  настройке — в README.md, раздел «Настройка email-верификации (Selectel)».

### 3.2 Запуск бэка

```bash
cd /opt/otherside/OtherSideServer
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
```

Проверка:

```bash
curl http://127.0.0.1:8000/health
# {"status":"ok"}
```

Логи:

```bash
docker compose -f docker-compose.prod.yml logs -f api
```

---

## Часть 4. Фронтенд (OtherSideFrontend)

### 4.1 Dockerfile

Создай **`OtherSideFrontend/Dockerfile`**:

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

ARG NEXT_PUBLIC_API_BASE_URL
ARG NEXT_PUBLIC_ADMIN_ROLE_IDS
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
ENV NEXT_PUBLIC_ADMIN_ROLE_IDS=$NEXT_PUBLIC_ADMIN_ROLE_IDS

RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

RUN addgroup -S nodejs && adduser -S nextjs -G nodejs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]
```

> В `next.config.ts` уже должен быть `output: 'standalone'`.

### 4.2 `docker-compose.prod.yml` для фронта

Создай **`OtherSideFrontend/docker-compose.prod.yml`**:

```yaml
services:
  frontend:
    build:
      context: .
      dockerfile: Dockerfile
      args:
        NEXT_PUBLIC_API_BASE_URL: https://api.otherside-inc.ru
        NEXT_PUBLIC_ADMIN_ROLE_IDS: ${NEXT_PUBLIC_ADMIN_ROLE_IDS:-}
    restart: unless-stopped
    ports:
      - "127.0.0.1:3000:3000"
```

Подставь свой домен и UUID админ-роли (если нужна админка).

Опционально создай `.env` рядом:

```env
NEXT_PUBLIC_ADMIN_ROLE_IDS=550e8400-e29b-41d4-a716-446655440000
```

### 4.3 Сборка и запуск

```bash
cd /opt/otherside/OtherSideFrontend
docker compose -f docker-compose.prod.yml up -d --build
```

Проверка:

```bash
curl -I http://127.0.0.1:3000
```

---

## Часть 5. Nginx

### 5.1 Удали дефолтный сайт

```bash
rm -f /etc/nginx/sites-enabled/default
```

### 5.2 API — `api.otherside.ru`

```bash
nano /etc/nginx/sites-available/otherside-api
```

```nginx
server {
    listen 80;
    server_name api.otherside.ru;

    client_max_body_size 20m;

    # Only proxy the real API surface + health check. Everything else gets a flat
    # 404 from nginx itself, so scanner noise (.env, wp-login.php, firebase keys, ...)
    # never reaches uvicorn. See deploy/nginx/otherside-api.conf for the canonical copy.
    location ~ ^/(api/|health$) {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }

    location / {
        return 404;
    }
}
```

### 5.3 Сайт — `otherside.ru` + `www`

```bash
nano /etc/nginx/sites-available/otherside-web
```

```nginx
server {
    listen 80;
    server_name otherside.ru www.otherside.ru;

    client_max_body_size 20m;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 60s;
    }
}
```

### 5.4 Включи сайты

**Сначала** создай оба файла в `sites-available` (разделы 5.2 и 5.3), **потом** делай симлинки. Иначе в `sites-enabled` появится битая ссылка и `nginx -t` упадёт.

Проверь, что оба конфига на месте:

```bash
ls -la /etc/nginx/sites-available/otherside-api /etc/nginx/sites-available/otherside-web
```

Оба файла должны существовать. Только после этого:

```bash
ln -sf /etc/nginx/sites-available/otherside-api /etc/nginx/sites-enabled/
ln -sf /etc/nginx/sites-available/otherside-web /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx
```

Проверь по HTTP (до SSL):

```bash
curl -I http://api.otherside-inc.ru/health
curl -I http://otherside-inc.ru
```

### 5.5 Ошибка reload: `open() ".../otherside-web" failed (2: No such file or directory)`

Если `systemctl reload nginx` или `nginx -t` падают с такой ошибкой — симлинк в `sites-enabled` есть, а файла в `sites-available` нет (часто забыли создать `otherside-web`, а `otherside-api` уже добавили).

Диагностика:

```bash
ls -la /etc/nginx/sites-enabled/
ls -la /etc/nginx/sites-available/
nginx -t
```

Пример проблемы: в `sites-enabled` есть `otherside-web -> .../otherside-web`, а в `sites-available` только `otherside-api` и `default`.

Исправление — создай недостающий файл (содержимое из раздела 5.3), затем:

```bash
ln -sf /etc/nginx/sites-available/otherside-web /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx
```

Успешный `nginx -t`:

```text
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

> Nginx может оставаться `active (running)` со старым конфигом, даже если reload не прошёл. Всегда проверяй `nginx -t` перед `systemctl reload nginx`.

---

## Часть 6. SSL (Let's Encrypt)

```bash https://otherside-inc.ru/
certbot --nginx \
  -d otherside-inc.ru \
  -d www.otherside-inc.ru \
  -d api.otherside-inc.ru
```

- Укажи email
- Согласись с ToS
- Выбери редирект HTTP → HTTPS (рекомендуется)

Проверка автообновления:

```bash
certbot renew --dry-run
```

После certbot в конфигах Nginx появятся блоки `listen 443 ssl` — это нормально.

---

## Часть 7. Fail2ban (бан сканеров)

Любой публичный домен сразу начинает получать фоновый шум от ботов, которые ищут `.env`,
`wp-login.php`, `firebase-adminsdk.json`, `/owa/` и т.п. Раздел 5.2 уже режет это на уровне
nginx (всё, кроме `/api/*` и `/health`, получает 404 не доходя до приложения), но banнить сами
IP полезно дополнительно — меньше шума в логах и меньше нагрузки на nginx.

```bash
apt install -y fail2ban
```

Скопируй фильтр и джейл из репозитория (`OtherSideServer/deploy/fail2ban/`):

```bash
scp deploy/fail2ban/filter.d/otherside-nginx-404.conf root@<server>:/etc/fail2ban/filter.d/
scp deploy/fail2ban/jail.d/otherside-nginx-404.conf root@<server>:/etc/fail2ban/jail.d/
```

Перезапусти и проверь:

```bash
systemctl restart fail2ban
fail2ban-client status otherside-nginx-404
```

Джейл банит IP, который за 5 минут получил 15+ ответов `404` от nginx (порог намеренно
щедрый, чтобы не задеть реальных пользователей) — на 1 час. Разбанить вручную:

```bash
fail2ban-client set otherside-nginx-404 unbanip <IP>
```

---

## Часть 8. Финальная проверка

| URL | Ожидание |
|-----|----------|
| `https://otherside.ru` | Лендинг |
| `https://otherside.ru/login` | Авторизация |
| `https://api.otherside.ru/health` | `{"status":"ok"}` |
| `https://api.otherside.ru/api/docs` | Swagger |

Проверь регистрацию → логин → dashboard.

**CORS error в браузере:**

1. Проверь `CORS_ORIGINS` в `.env` бэка (точные `https://`, без `/` в конце)
2. Перезапусти API:

```bash
docker compose -f docker-compose.prod.yml restart api
```

**Фронт обращается к `localhost:8000`:**

Пересобери фронт с правильным `NEXT_PUBLIC_API_BASE_URL` — эта переменная вшивается **при сборке**.

---

## Часть 9. Обновление после изменений в коде

### Бэкенд

```bash
cd /opt/otherside/OtherSideServer
git pull
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
```

### Фронтенд

```bash
cd /opt/otherside/OtherSideFrontend
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

---

## Часть 10. Автозапуск

Docker с `restart: unless-stopped` поднимет контейнеры после перезагрузки. Nginx:

```bash
systemctl enable nginx
```

---

## Часть 11. Чеклист безопасности

- [ ] `DEBUG=false` на бэке
- [ ] `SECRET_KEY` — случайный (`openssl rand -hex 32`), не из примера
- [ ] Пароль Postgres — сильный
- [ ] Порты `3000`, `8000`, `5432` **не** открыты в firewall наружу
- [ ] `.env` не коммитится в git
- [ ] `CORS_ORIGINS` — только твои домены, не `["*"]`
- [ ] SSH по ключу (по желанию отключить вход по паролю)
- [ ] nginx `otherside-api` проксирует только `/api/*` и `/health` (раздел 5.2)
- [ ] fail2ban джейл `otherside-nginx-404` активен (раздел 7)

---

## Часть 12. Типичные проблемы

| Проблема | Решение |
|----------|---------|
| Домен не открывается | Проверь A-записи DNS, подожди 5–30 мин |
| 502 Bad Gateway | `docker ps` — контейнер упал; смотри логи |
| CORS | Исправь `CORS_ORIGINS`, перезапусти api |
| Фронт бьётся в `localhost:8000` | Пересобери с `NEXT_PUBLIC_API_BASE_URL=https://api...` |
| Certbot не выдаёт сертификат | DNS → IP сервера, порт 80 открыт |
| 413 Request Entity Too Large | Увеличь `client_max_body_size` в nginx |
| `nginx -t` / reload: `open() ".../otherside-web" failed` | Создай файл в `sites-available` (раздел 5.3), затем симлинк — см. раздел 5.5 |

---

## Шпаргалка команд

```bash
# Статус
docker ps
systemctl status nginx

# Логи
docker compose -f /opt/otherside/OtherSideServer/docker-compose.prod.yml logs -f api
docker compose -f /opt/otherside/OtherSideFrontend/docker-compose.prod.yml logs -f frontend

# Перезапуск
cd /opt/otherside/OtherSideServer && docker compose -f docker-compose.prod.yml restart
cd /opt/otherside/OtherSideFrontend && docker compose -f docker-compose.prod.yml restart
systemctl reload nginx
```

---

## Связанные документы

- [OtherSideServer/README.md](./OtherSideServer/README.md) — API, миграции, локальный Docker
- [OtherSideFrontend/README.md](./OtherSideFrontend/README.md) — фронтенд, env-переменные
- [OtherSideServer/deploy/](./OtherSideServer/deploy/) — актуальные копии конфигов nginx/fail2ban с прод-сервера

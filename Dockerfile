# syntax=docker/dockerfile:1

FROM python:3.14-slim AS builder

WORKDIR /app

RUN pip install --no-cache-dir hatchling

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip wheel --no-cache-dir --wheel-dir /wheels .

FROM python:3.14-slim AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*.whl && rm -rf /wheels

COPY src ./src
COPY migrations ./migrations
COPY alembic.ini ./

# Drop root: an RCE/container-escape then starts from an unprivileged account.
RUN adduser --system --no-create-home --group app \
    && chown -R app:app /app
USER app

EXPOSE 8000

# --proxy-headers + --forwarded-allow-ips lets uvicorn trust X-Forwarded-For from
# the reverse proxy, so request.client.host (used for rate-limit keying and logs)
# is the real client IP instead of the proxy's. The app is only reachable through
# the proxy (prod binds 127.0.0.1), so trusting the immediate peer is safe here.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--forwarded-allow-ips", "*"]

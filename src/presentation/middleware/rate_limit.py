"""In-memory rate limiting middleware for sensitive endpoints."""

from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from config.settings import settings
from presentation.api.v1.schemas.responses import ErrorResponse

_RATE_LIMIT_RULES: dict[str, tuple[int, int]] = {
    "/api/v1/auth/login": (
        settings.RATE_LIMIT_AUTH_REQUESTS,
        settings.RATE_LIMIT_AUTH_WINDOW_SECONDS,
    ),
    "/api/v1/auth/register": (
        settings.RATE_LIMIT_AUTH_REQUESTS,
        settings.RATE_LIMIT_AUTH_WINDOW_SECONDS,
    ),
    "/api/v1/auth/verify-email": (
        settings.RATE_LIMIT_AUTH_REQUESTS,
        settings.RATE_LIMIT_AUTH_WINDOW_SECONDS,
    ),
    "/api/v1/auth/resend-verification": (
        settings.RATE_LIMIT_AUTH_REQUESTS,
        settings.RATE_LIMIT_AUTH_WINDOW_SECONDS,
    ),
    "/api/v1/auth/refresh": (
        settings.RATE_LIMIT_AUTH_REQUESTS,
        settings.RATE_LIMIT_AUTH_WINDOW_SECONDS,
    ),
    "/api/v1/auth/logout": (
        settings.RATE_LIMIT_AUTH_REQUESTS,
        settings.RATE_LIMIT_AUTH_WINDOW_SECONDS,
    ),
    "/api/v1/auth/change-password": (
        settings.RATE_LIMIT_AUTH_REQUESTS,
        settings.RATE_LIMIT_AUTH_WINDOW_SECONDS,
    ),
    "/api/v1/contact/submissions": (
        settings.RATE_LIMIT_CONTACT_REQUESTS,
        settings.RATE_LIMIT_CONTACT_WINDOW_SECONDS,
    ),
    "/api/v1/payments/robokassa/result": (
        settings.RATE_LIMIT_WEBHOOK_REQUESTS,
        settings.RATE_LIMIT_WEBHOOK_WINDOW_SECONDS,
    ),
}


class _InMemoryRateLimiter:
    def __init__(self) -> None:
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def is_allowed(self, key: str, limit: int, window_seconds: int) -> bool:
        now = time.monotonic()
        with self._lock:
            timestamps = self._requests[key]
            timestamps[:] = [
                timestamp for timestamp in timestamps if now - timestamp < window_seconds
            ]
            if len(timestamps) >= limit:
                return False
            timestamps.append(now)
            return True


_rate_limiter = _InMemoryRateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Reject excessive requests to auth, contact, and payment webhook endpoints."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        rule = _RATE_LIMIT_RULES.get(request.url.path)
        if rule is None or request.method == "OPTIONS":
            return await call_next(request)

        limit, window_seconds = rule
        client_ip = request.client.host if request.client else "unknown"
        key = f"{request.url.path}:{client_ip}"

        if not _rate_limiter.is_allowed(key, limit, window_seconds):
            return JSONResponse(
                status_code=429,
                content=ErrorResponse(
                    detail="Too many requests. Please try again later.",
                    code="rate_limit_exceeded",
                ).model_dump(),
            )

        return await call_next(request)

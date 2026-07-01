"""Maintenance mode middleware — blocks non-admin users when enabled."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from application.auth import ADMIN_ROLE_NAME
from config.security import get_user_id_from_token
from domain.exceptions import AuthenticationError
from infrastructure.db.models import RoleModel, SystemSettingsModel, UserModel
from presentation.api.v1.schemas.responses import ErrorResponse
from infrastructure.cache.maintenance_cache import MaintenanceModeCache

logger = logging.getLogger(__name__)

BYPASS_PATHS = frozenset({
    "/health",
    "/api/docs",
    "/api/redoc",
    "/api/openapi.json",
    "/api/v1/auth/login",
    "/api/v1/settings/maintenance",
})

MAINTENANCE_MESSAGE = "Service is temporarily unavailable due to scheduled maintenance"


class MaintenanceMiddleware(BaseHTTPMiddleware):
    """Reject requests from non-admin users when maintenance mode is active."""

    def __init__(
        self,
        app,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        super().__init__(app)
        self._session_factory = session_factory

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in BYPASS_PATHS:
            return await call_next(request)

        maintenance_enabled = await self._is_maintenance_enabled()
        if not maintenance_enabled:
            return await call_next(request)

        if await self._is_admin_request(request):
            return await call_next(request)

        return JSONResponse(
            status_code=503,
            content=ErrorResponse(
                detail=MAINTENANCE_MESSAGE,
                code="maintenance",
            ).model_dump(),
        )

    async def _is_maintenance_enabled(self) -> bool:
        cached = MaintenanceModeCache.get()
        if cached is not None:
            return cached

        try:
            async with self._session_factory() as session:
                result = await session.execute(
                    select(SystemSettingsModel.maintenance_mode).where(
                        SystemSettingsModel.id == 1
                    )
                )
                value = result.scalar_one_or_none()
                enabled = bool(value) if value is not None else False
                MaintenanceModeCache.set(enabled)
                return enabled
        except Exception:
            logger.exception("Failed to read maintenance mode from database")
            return False

    async def _is_admin_request(self, request: Request) -> bool:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return False

        token = auth_header.removeprefix("Bearer ").strip()
        if not token:
            return False

        try:
            user_id = get_user_id_from_token(token)
        except AuthenticationError:
            return False

        try:
            async with self._session_factory() as session:
                result = await session.execute(
                    select(RoleModel.role)
                    .join(UserModel, UserModel.role_id == RoleModel.id)
                    .where(UserModel.id == user_id)
                )
                role_name: str | None = result.scalar_one_or_none()
                return role_name == ADMIN_ROLE_NAME
        except Exception:
            logger.exception("Failed to resolve admin role for user_id=%s", user_id)
            return False

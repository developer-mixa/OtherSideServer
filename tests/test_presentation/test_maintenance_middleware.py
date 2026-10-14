"""MaintenanceMiddleware against the real database it reads the flag and roles from."""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from config.security import create_access_token
from infrastructure.cache.maintenance_cache import MaintenanceModeCache
from infrastructure.db.models import RoleModel, SystemSettingsModel, UserModel


async def _set_maintenance(factory: async_sessionmaker[AsyncSession], enabled: bool) -> None:
    async with factory() as session:
        await session.execute(
            update(SystemSettingsModel)
            .where(SystemSettingsModel.id == 1)
            .values(maintenance_mode=enabled)
        )
        await session.commit()
    MaintenanceModeCache.invalidate()


@pytest.fixture
async def maintenance_on(
    committing_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[None]:
    await _set_maintenance(committing_session_factory, True)
    try:
        yield
    finally:
        await _set_maintenance(committing_session_factory, False)


@pytest.fixture
async def db_admin_headers(
    committing_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[dict[str, str]]:
    """An admin that exists in PostgreSQL, where the middleware looks roles up."""
    user_id = uuid4()
    async with committing_session_factory() as session:
        admin_role_id = (
            await session.execute(select(RoleModel.id).where(RoleModel.role == "admin"))
        ).scalar_one()
        session.add(
            UserModel(
                id=user_id,
                username=f"mm-admin-{user_id.hex[:8]}",
                email=f"mm-admin-{user_id.hex[:8]}@example.com",
                password_hash="unused",
                is_verified=True,
                role_id=admin_role_id,
            )
        )
        await session.commit()
    try:
        yield {"Authorization": f"Bearer {create_access_token({'sub': str(user_id)})}"}
    finally:
        async with committing_session_factory() as session:
            await session.execute(delete(UserModel).where(UserModel.id == user_id))
            await session.commit()


class TestMaintenanceMiddleware:
    async def test_requests_pass_when_maintenance_is_off(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/plans")
        assert response.status_code == 200

    @pytest.mark.usefixtures("maintenance_on")
    async def test_anonymous_request_gets_503(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/plans")
        assert response.status_code == 503
        assert response.json()["code"] == "maintenance"

    @pytest.mark.usefixtures("maintenance_on")
    async def test_bypass_paths_stay_reachable(self, client: AsyncClient) -> None:
        assert (await client.get("/health")).status_code == 200
        refresh = await client.post("/api/v1/auth/refresh", json={"refresh_token": "nope"})
        assert refresh.status_code == 401

    @pytest.mark.usefixtures("maintenance_on")
    async def test_admin_is_let_through(
        self, client: AsyncClient, db_admin_headers: dict[str, str]
    ) -> None:
        response = await client.get("/api/v1/plans", headers=db_admin_headers)
        assert response.status_code == 200

    @pytest.mark.usefixtures("maintenance_on")
    async def test_regular_user_token_gets_503(self, client: AsyncClient) -> None:
        headers = {"Authorization": f"Bearer {create_access_token({'sub': str(uuid4())})}"}
        response = await client.get("/api/v1/plans", headers=headers)
        assert response.status_code == 503

    @pytest.mark.usefixtures("maintenance_on")
    async def test_garbage_token_gets_503(self, client: AsyncClient) -> None:
        for header in ("Bearer not-a-jwt", "Bearer ", "Basic abc"):
            response = await client.get("/api/v1/plans", headers={"Authorization": header})
            assert response.status_code == 503

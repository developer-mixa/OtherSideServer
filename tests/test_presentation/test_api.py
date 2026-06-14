"""API endpoint tests."""

from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient

from config.security import hash_password
from domain.entities import CompanyGame, SubscriptionPlan, User
from tests.conftest import FakeUnitOfWork


class TestHealthEndpoint:
    async def test_health(self, client: AsyncClient) -> None:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestAuthEndpoints:
    async def test_register(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "newuser",
                "email": "new@example.com",
                "password": "password123",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "new@example.com"

    async def test_login(self, client: AsyncClient, fake_uow: FakeUnitOfWork) -> None:
        user = User.create("loginuser", "login@example.com", hash_password("password123"))
        fake_uow._store.users[user.id] = user
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "login@example.com", "password": "password123"},
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

    async def test_me_authenticated(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["username"] == "testuser"

    async def test_me_unauthenticated(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401


class TestRolesEndpoints:
    async def test_create_and_list_roles(self, client: AsyncClient) -> None:
        create_resp = await client.post("/api/v1/roles", json={"role": "admin"})
        assert create_resp.status_code == 201
        list_resp = await client.get("/api/v1/roles")
        assert list_resp.status_code == 200
        assert len(list_resp.json()) == 1


class TestGamesEndpoints:
    async def test_create_game(self, client: AsyncClient) -> None:
        response = await client.post("/api/v1/games", json={"game": "CS2"})
        assert response.status_code == 201
        assert response.json()["game"] == "CS2"

    async def test_delete_game(self, client: AsyncClient, fake_uow: FakeUnitOfWork) -> None:
        game = CompanyGame.create("Dota2")
        fake_uow._store.company_games[game.id] = game
        response = await client.delete(f"/api/v1/games/{game.id}")
        assert response.status_code == 204


class TestPlansEndpoints:
    async def test_create_plan(self, client: AsyncClient, fake_uow: FakeUnitOfWork) -> None:
        game = CompanyGame.create("Minecraft")
        fake_uow._store.company_games[game.id] = game
        response = await client.post(
            "/api/v1/plans",
            json={"type": "monthly", "game_id": str(game.id)},
        )
        assert response.status_code == 201
        assert response.json()["type"] == "monthly"


class TestSubscriptionsEndpoints:
    async def test_create_subscription(
        self, client: AsyncClient, fake_uow: FakeUnitOfWork
    ) -> None:
        user = User.create("subuser", "sub@example.com", "hash")
        fake_uow._store.users[user.id] = user
        response = await client.post(
            "/api/v1/subscriptions",
            json={"user_id": str(user.id)},
        )
        assert response.status_code == 201


class TestPromocodesEndpoints:
    async def test_create_promocode(
        self, client: AsyncClient, fake_uow: FakeUnitOfWork
    ) -> None:
        plan = SubscriptionPlan.create("monthly")
        fake_uow._store.subscription_plans[plan.id] = plan
        response = await client.post(
            "/api/v1/promocodes",
            json={"code": "SAVE10", "plan_id": str(plan.id)},
        )
        assert response.status_code == 201
        assert response.json()["code"] == "SAVE10"


class TestPaymentsEndpoints:
    async def test_create_payment(self, client: AsyncClient, fake_uow: FakeUnitOfWork) -> None:
        user = User.create("payuser", "pay@example.com", "hash")
        plan = SubscriptionPlan.create("monthly")
        fake_uow._store.users[user.id] = user
        fake_uow._store.subscription_plans[plan.id] = plan
        response = await client.post(
            "/api/v1/payments",
            json={
                "user_id": str(user.id),
                "plan_id": str(plan.id),
                "amount": "99.99",
                "status": "pending",
                "robokassa_invoice_id": "inv-123",
                "idempotency_key": "idem-123",
            },
        )
        assert response.status_code == 201
        assert response.json()["amount"] == "99.99"

    async def test_list_my_payments(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        response = await client.get("/api/v1/payments/me", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

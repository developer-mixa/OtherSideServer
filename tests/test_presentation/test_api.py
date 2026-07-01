"""API endpoint tests."""

from uuid import uuid4

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
    async def test_create_and_list_roles_requires_admin(
        self, client: AsyncClient, admin_headers: dict[str, str]
    ) -> None:
        create_resp = await client.post(
            "/api/v1/roles", json={"role": "moderator"}, headers=admin_headers
        )
        assert create_resp.status_code == 201
        list_resp = await client.get("/api/v1/roles", headers=admin_headers)
        assert list_resp.status_code == 200
        assert any(role["role"] == "moderator" for role in list_resp.json())

    async def test_list_roles_forbidden_for_regular_user(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        response = await client.get("/api/v1/roles", headers=auth_headers)
        assert response.status_code == 403

    async def test_list_roles_unauthenticated(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/roles")
        assert response.status_code == 401


class TestGamesEndpoints:
    async def test_create_game_requires_admin(
        self, client: AsyncClient, admin_headers: dict[str, str]
    ) -> None:
        response = await client.post(
            "/api/v1/games", json={"game": "CS2"}, headers=admin_headers
        )
        assert response.status_code == 201
        assert response.json()["game"] == "CS2"

    async def test_create_game_unauthenticated(self, client: AsyncClient) -> None:
        response = await client.post("/api/v1/games", json={"game": "CS2"})
        assert response.status_code == 401

    async def test_delete_game(
        self, client: AsyncClient, fake_uow: FakeUnitOfWork, admin_headers: dict[str, str]
    ) -> None:
        game = CompanyGame.create("Dota2")
        fake_uow._store.company_games[game.id] = game
        response = await client.delete(f"/api/v1/games/{game.id}", headers=admin_headers)
        assert response.status_code == 204


class TestPlansEndpoints:
    async def test_list_plans_public(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/plans")
        assert response.status_code == 200

    async def test_create_plan_requires_admin(
        self, client: AsyncClient, fake_uow: FakeUnitOfWork, admin_headers: dict[str, str]
    ) -> None:
        game = CompanyGame.create("Minecraft")
        fake_uow._store.company_games[game.id] = game
        response = await client.post(
            "/api/v1/plans",
            json={"type": "monthly", "game_id": str(game.id)},
            headers=admin_headers,
        )
        assert response.status_code == 201
        assert response.json()["type"] == "monthly"


class TestSubscriptionsEndpoints:
    async def test_create_subscription_requires_admin(
        self, client: AsyncClient, fake_uow: FakeUnitOfWork, admin_headers: dict[str, str]
    ) -> None:
        user = User.create("subuser", "sub@example.com", "hash")
        fake_uow._store.users[user.id] = user
        response = await client.post(
            "/api/v1/subscriptions",
            json={"user_id": str(user.id)},
            headers=admin_headers,
        )
        assert response.status_code == 201

    async def test_create_subscription_forbidden_for_regular_user(
        self, client: AsyncClient, fake_uow: FakeUnitOfWork, auth_headers: dict[str, str]
    ) -> None:
        user = User.create("subuser2", "sub2@example.com", "hash")
        fake_uow._store.users[user.id] = user
        response = await client.post(
            "/api/v1/subscriptions",
            json={"user_id": str(user.id)},
            headers=auth_headers,
        )
        assert response.status_code == 403

    async def test_list_own_subscriptions(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        response = await client.get("/api/v1/subscriptions", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_list_subscriptions_unauthenticated(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/subscriptions")
        assert response.status_code == 401


class TestPromocodesEndpoints:
    async def test_create_promocode_requires_admin(
        self, client: AsyncClient, fake_uow: FakeUnitOfWork, admin_headers: dict[str, str]
    ) -> None:
        plan = SubscriptionPlan.create("monthly")
        fake_uow._store.subscription_plans[plan.id] = plan
        response = await client.post(
            "/api/v1/promocodes",
            json={"code": "SAVE10", "plan_id": str(plan.id)},
            headers=admin_headers,
        )
        assert response.status_code == 201
        assert response.json()["code"] == "SAVE10"

    async def test_list_promocodes_unauthenticated(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/promocodes")
        assert response.status_code == 401


class TestPaymentsEndpoints:
    async def test_initiate_payment(
        self, client: AsyncClient, fake_uow: FakeUnitOfWork, auth_headers: dict[str, str]
    ) -> None:
        from decimal import Decimal

        plan = SubscriptionPlan.create("remove_ad", price_amount=Decimal("499.00"))
        fake_uow._store.subscription_plans[plan.id] = plan
        response = await client.post(
            "/api/v1/payments/init",
            headers=auth_headers,
            json={
                "plan_id": str(plan.id),
                "idempotency_key": "idem-init-123",
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "pending"
        assert body["amount"] == "499.00"
        assert "payment_url" in body
        assert "robokassa_invoice_id" in body

    async def test_initiate_payment_requires_auth(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/payments/init",
            json={"plan_id": str(uuid4()), "idempotency_key": "idem-no-auth"},
        )
        assert response.status_code == 401

    async def test_list_my_payments(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        response = await client.get("/api/v1/payments/me", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestSecurityHeaders:
    async def test_security_headers_present(self, client: AsyncClient) -> None:
        response = await client.get("/health")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"

"""API endpoint tests."""

from uuid import uuid4

from httpx import AsyncClient

from config.security import hash_password
from domain.entities import CompanyGame, PromocodeEntity, Subscription, SubscriptionPlan, User
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

    async def test_update_game(
        self, client: AsyncClient, fake_uow: FakeUnitOfWork, admin_headers: dict[str, str]
    ) -> None:
        game = CompanyGame.create("OldGame")
        fake_uow._store.company_games[game.id] = game
        response = await client.patch(
            f"/api/v1/games/{game.id}", json={"game": "NewGame"}, headers=admin_headers
        )
        assert response.status_code == 200
        assert response.json()["game"] == "NewGame"

    async def test_update_game_not_found(
        self, client: AsyncClient, admin_headers: dict[str, str]
    ) -> None:
        response = await client.patch(
            f"/api/v1/games/{uuid4()}", json={"game": "X"}, headers=admin_headers
        )
        assert response.status_code == 404

    async def test_update_game_forbidden_for_regular_user(
        self, client: AsyncClient, fake_uow: FakeUnitOfWork, auth_headers: dict[str, str]
    ) -> None:
        game = CompanyGame.create("Game")
        fake_uow._store.company_games[game.id] = game
        response = await client.patch(
            f"/api/v1/games/{game.id}", json={"game": "X"}, headers=auth_headers
        )
        assert response.status_code == 403


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
            json={"type": "monthly", "game_id": str(game.id), "duration_days": 30},
            headers=admin_headers,
        )
        assert response.status_code == 201
        body = response.json()
        assert body["type"] == "monthly"
        assert body["duration_days"] == 30

    async def test_update_plan(
        self, client: AsyncClient, fake_uow: FakeUnitOfWork, admin_headers: dict[str, str]
    ) -> None:
        plan = SubscriptionPlan.create("monthly")
        fake_uow._store.subscription_plans[plan.id] = plan
        response = await client.patch(
            f"/api/v1/plans/{plan.id}",
            json={"type": "yearly", "is_active": False, "duration_days": 365},
            headers=admin_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["type"] == "yearly"
        assert body["is_active"] is False
        assert body["duration_days"] == 365

    async def test_update_plan_not_found(
        self, client: AsyncClient, admin_headers: dict[str, str]
    ) -> None:
        response = await client.patch(
            f"/api/v1/plans/{uuid4()}", json={"type": "yearly"}, headers=admin_headers
        )
        assert response.status_code == 404

    async def test_delete_plan(
        self, client: AsyncClient, fake_uow: FakeUnitOfWork, admin_headers: dict[str, str]
    ) -> None:
        plan = SubscriptionPlan.create("monthly")
        fake_uow._store.subscription_plans[plan.id] = plan
        response = await client.delete(f"/api/v1/plans/{plan.id}", headers=admin_headers)
        assert response.status_code == 204

    async def test_update_plan_forbidden_for_regular_user(
        self, client: AsyncClient, fake_uow: FakeUnitOfWork, auth_headers: dict[str, str]
    ) -> None:
        plan = SubscriptionPlan.create("monthly")
        fake_uow._store.subscription_plans[plan.id] = plan
        response = await client.patch(
            f"/api/v1/plans/{plan.id}", json={"type": "yearly"}, headers=auth_headers
        )
        assert response.status_code == 403


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

    async def test_update_subscription(
        self, client: AsyncClient, fake_uow: FakeUnitOfWork, admin_headers: dict[str, str]
    ) -> None:
        user = User.create("subuser4", "sub4@example.com", "hash")
        fake_uow._store.users[user.id] = user
        plan = SubscriptionPlan.create("monthly")
        fake_uow._store.subscription_plans[plan.id] = plan
        sub = Subscription.create(user_id=user.id)
        fake_uow._store.subscriptions[sub.id] = sub
        response = await client.patch(
            f"/api/v1/subscriptions/{sub.id}",
            json={"plan_id": str(plan.id)},
            headers=admin_headers,
        )
        assert response.status_code == 200
        assert response.json()["plan_id"] == str(plan.id)

    async def test_update_subscription_not_found(
        self, client: AsyncClient, admin_headers: dict[str, str]
    ) -> None:
        response = await client.patch(
            f"/api/v1/subscriptions/{uuid4()}", json={}, headers=admin_headers
        )
        assert response.status_code == 404

    async def test_delete_subscription(
        self, client: AsyncClient, fake_uow: FakeUnitOfWork, admin_headers: dict[str, str]
    ) -> None:
        user = User.create("subuser5", "sub5@example.com", "hash")
        fake_uow._store.users[user.id] = user
        sub = Subscription.create(user_id=user.id)
        fake_uow._store.subscriptions[sub.id] = sub
        response = await client.delete(
            f"/api/v1/subscriptions/{sub.id}", headers=admin_headers
        )
        assert response.status_code == 204

    async def test_update_subscription_forbidden_for_regular_user(
        self, client: AsyncClient, fake_uow: FakeUnitOfWork, auth_headers: dict[str, str]
    ) -> None:
        user = User.create("subuser6", "sub6@example.com", "hash")
        fake_uow._store.users[user.id] = user
        sub = Subscription.create(user_id=user.id)
        fake_uow._store.subscriptions[sub.id] = sub
        response = await client.patch(
            f"/api/v1/subscriptions/{sub.id}", json={}, headers=auth_headers
        )
        assert response.status_code == 403


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

    async def test_update_promocode(
        self, client: AsyncClient, fake_uow: FakeUnitOfWork, admin_headers: dict[str, str]
    ) -> None:
        plan = SubscriptionPlan.create("monthly")
        fake_uow._store.subscription_plans[plan.id] = plan
        code = PromocodeEntity.create("SAVE10", plan.id)
        fake_uow._store.promocodes[code.id] = code
        response = await client.patch(
            f"/api/v1/promocodes/{code.id}",
            json={"is_active": False},
            headers=admin_headers,
        )
        assert response.status_code == 200
        assert response.json()["is_active"] is False

    async def test_update_promocode_not_found(
        self, client: AsyncClient, admin_headers: dict[str, str]
    ) -> None:
        response = await client.patch(
            f"/api/v1/promocodes/{uuid4()}", json={"is_active": False}, headers=admin_headers
        )
        assert response.status_code == 404

    async def test_delete_promocode(
        self, client: AsyncClient, fake_uow: FakeUnitOfWork, admin_headers: dict[str, str]
    ) -> None:
        plan = SubscriptionPlan.create("monthly")
        fake_uow._store.subscription_plans[plan.id] = plan
        code = PromocodeEntity.create("DEL10", plan.id)
        fake_uow._store.promocodes[code.id] = code
        response = await client.delete(
            f"/api/v1/promocodes/{code.id}", headers=admin_headers
        )
        assert response.status_code == 204

    async def test_update_promocode_forbidden_for_regular_user(
        self, client: AsyncClient, fake_uow: FakeUnitOfWork, auth_headers: dict[str, str]
    ) -> None:
        plan = SubscriptionPlan.create("monthly")
        fake_uow._store.subscription_plans[plan.id] = plan
        code = PromocodeEntity.create("SAVE30", plan.id)
        fake_uow._store.promocodes[code.id] = code
        response = await client.patch(
            f"/api/v1/promocodes/{code.id}", json={"is_active": False}, headers=auth_headers
        )
        assert response.status_code == 403


class TestUsersEndpoints:
    async def test_list_users_requires_admin(
        self, client: AsyncClient, fake_uow: FakeUnitOfWork, admin_headers: dict[str, str]
    ) -> None:
        response = await client.get("/api/v1/users", headers=admin_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_list_users_forbidden_for_regular_user(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        response = await client.get("/api/v1/users", headers=auth_headers)
        assert response.status_code == 403

    async def test_list_users_unauthenticated(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/users")
        assert response.status_code == 401

    async def test_update_user_block(
        self, client: AsyncClient, fake_uow: FakeUnitOfWork, admin_headers: dict[str, str]
    ) -> None:
        user = User.create("targetuser", "targetuser@example.com", "hash")
        fake_uow._store.users[user.id] = user
        response = await client.patch(
            f"/api/v1/users/{user.id}",
            json={"is_blocked": True},
            headers=admin_headers,
        )
        assert response.status_code == 200
        assert response.json()["is_blocked"] is True

    async def test_update_user_not_found(
        self, client: AsyncClient, admin_headers: dict[str, str]
    ) -> None:
        response = await client.patch(
            f"/api/v1/users/{uuid4()}", json={"is_blocked": True}, headers=admin_headers
        )
        assert response.status_code == 404

    async def test_update_user_forbidden_for_regular_user(
        self, client: AsyncClient, fake_uow: FakeUnitOfWork, auth_headers: dict[str, str]
    ) -> None:
        user = User.create("targetuser2", "targetuser2@example.com", "hash")
        fake_uow._store.users[user.id] = user
        response = await client.patch(
            f"/api/v1/users/{user.id}", json={"is_blocked": True}, headers=auth_headers
        )
        assert response.status_code == 403

    async def test_login_rejected_for_blocked_user(
        self, client: AsyncClient, fake_uow: FakeUnitOfWork, admin_headers: dict[str, str]
    ) -> None:
        user = User.create("blockeduser2", "blockeduser2@example.com", hash_password("password123"))
        fake_uow._store.users[user.id] = user
        block_resp = await client.patch(
            f"/api/v1/users/{user.id}", json={"is_blocked": True}, headers=admin_headers
        )
        assert block_resp.status_code == 200
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "blockeduser2@example.com", "password": "password123"},
        )
        assert login_resp.status_code == 403


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


class TestRobokassaResultWebhook:
    """Robokassa's default merchant config sends the Result URL as a GET request."""

    async def test_result_via_get(self, client: AsyncClient, fake_uow: FakeUnitOfWork) -> None:
        import hashlib
        from datetime import datetime
        from decimal import Decimal

        from config.settings import settings
        from domain.entities import Payment, SubscriptionPlan, User

        user = User.create("payer", "payer@example.com", "hash")
        fake_uow._store.users[user.id] = user
        plan = SubscriptionPlan.create("remove_ad", price_amount=Decimal("499.00"))
        fake_uow._store.subscription_plans[plan.id] = plan
        payment = Payment.create(
            user_id=user.id,
            plan_id=plan.id,
            amount=Decimal("499.00"),
            status="pending",
            robokassa_invoice_id="777001",
            idempotency_key="idem-get-webhook",
            now=datetime.utcnow(),
        )
        fake_uow._store.payments[payment.id] = payment

        password2 = settings.ROBOKASSA_PASSWORD2 or "password2"
        out_sum = "499.00"
        signature = hashlib.md5(
            f"{out_sum}:{payment.robokassa_invoice_id}:{password2}".encode()
        ).hexdigest()

        response = await client.get(
            "/api/v1/payments/robokassa/result",
            params={
                "OutSum": out_sum,
                "InvId": payment.robokassa_invoice_id,
                "SignatureValue": signature,
            },
        )
        assert response.status_code == 200
        assert response.text == f"OK{payment.robokassa_invoice_id}"

    async def test_result_rejects_invalid_signature(self, client: AsyncClient) -> None:
        response = await client.get(
            "/api/v1/payments/robokassa/result",
            params={"OutSum": "499.00", "InvId": "777002", "SignatureValue": "bad"},
        )
        assert response.status_code == 400


class TestSecurityHeaders:
    async def test_security_headers_present(self, client: AsyncClient) -> None:
        response = await client.get("/health")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"

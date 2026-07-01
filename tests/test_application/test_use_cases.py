"""Application use case tests."""

from decimal import Decimal
from uuid import uuid4

import pytest

from application.dtos import (
    CompanyGameCreateDTO,
    PaymentCreateDTO,
    PromocodeCreateDTO,
    SubscriptionCreateDTO,
    SubscriptionPlanCreateDTO,
    UserCreateDTO,
)
from application.use_cases import (
    CreateCompanyGameUseCase,
    CreatePaymentUseCase,
    CreatePromocodeUseCase,
    CreateRoleUseCase,
    CreateSubscriptionPlanUseCase,
    CreateSubscriptionUseCase,
    DeleteCompanyGameUseCase,
    GetCurrentUserUseCase,
    ListRolesUseCase,
    ListSubscriptionsUseCase,
    LoginUserUseCase,
    RegisterUserUseCase,
)
from config.security import hash_password
from domain.entities import CompanyGame, Role, SubscriptionPlan, User
from domain.exceptions import (
    AuthenticationError,
    AuthorizationError,
    DuplicateEntityError,
    EntityNotFoundError,
    ValidationError,
)
from tests.conftest import FakeUnitOfWork, make_admin_user


@pytest.fixture
def uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


class TestRegisterUserUseCase:
    async def test_register_success(self, uow: FakeUnitOfWork) -> None:
        use_case = RegisterUserUseCase(uow)
        dto = UserCreateDTO(username="newuser", email="new@example.com", password="password123")
        result = await use_case.execute(dto)
        assert result.username == "newuser"
        assert result.email == "new@example.com"
        assert result.is_admin is False

    async def test_register_always_assigns_user_role(self, uow: FakeUnitOfWork) -> None:
        use_case = RegisterUserUseCase(uow)
        dto = UserCreateDTO(username="plainuser", email="plain@example.com", password="password123")
        result = await use_case.execute(dto)
        user_role = await uow.roles.get_by_name("user")
        assert user_role is not None
        assert result.role_id == user_role.id

    async def test_register_duplicate_email(self, uow: FakeUnitOfWork) -> None:
        user = User.create("existing", "dup@example.com", "hash")
        uow._store.users[user.id] = user
        use_case = RegisterUserUseCase(uow)
        dto = UserCreateDTO(username="other", email="dup@example.com", password="password123")
        with pytest.raises(DuplicateEntityError):
            await use_case.execute(dto)


class TestLoginUserUseCase:
    async def test_login_success(self, uow: FakeUnitOfWork) -> None:
        user = User.create("loginuser", "login@example.com", hash_password("password123"))
        uow._store.users[user.id] = user
        use_case = LoginUserUseCase(uow)
        result = await use_case.execute("login@example.com", "password123")
        assert result.access_token

    async def test_login_wrong_password(self, uow: FakeUnitOfWork) -> None:
        user = User.create("loginuser", "login@example.com", hash_password("password123"))
        uow._store.users[user.id] = user
        use_case = LoginUserUseCase(uow)
        with pytest.raises(AuthenticationError):
            await use_case.execute("login@example.com", "wrongpass")


class TestGetCurrentUserUseCase:
    async def test_get_existing_user(self, uow: FakeUnitOfWork) -> None:
        user = User.create("me", "me@example.com", "hash")
        uow._store.users[user.id] = user
        result = await GetCurrentUserUseCase(uow).execute(user.id)
        assert result.email == "me@example.com"

    async def test_get_missing_user(self, uow: FakeUnitOfWork) -> None:
        with pytest.raises(EntityNotFoundError):
            await GetCurrentUserUseCase(uow).execute(uuid4())


class TestRoleUseCases:
    async def test_create_and_list_roles(self, uow: FakeUnitOfWork) -> None:
        admin = make_admin_user(uow._store)
        created = await CreateRoleUseCase(uow).execute(admin.id, "moderator")
        roles = await ListRolesUseCase(uow).execute(admin.id)
        assert created.role == "moderator"
        assert any(role.role == "moderator" for role in roles)

    async def test_create_duplicate_role(self, uow: FakeUnitOfWork) -> None:
        admin = make_admin_user(uow._store)
        uow._store.roles[uuid4()] = Role.create("custom-admin")
        with pytest.raises(DuplicateEntityError):
            await CreateRoleUseCase(uow).execute(admin.id, "custom-admin")

    async def test_list_roles_forbidden_for_regular_user(self, uow: FakeUnitOfWork) -> None:
        user = User.create("plain", "plain@example.com", "hash")
        uow._store.users[user.id] = user
        with pytest.raises(AuthorizationError):
            await ListRolesUseCase(uow).execute(user.id)


class TestCompanyGameUseCases:
    async def test_create_game(self, uow: FakeUnitOfWork) -> None:
        admin = make_admin_user(uow._store)
        result = await CreateCompanyGameUseCase(uow).execute(
            admin.id, CompanyGameCreateDTO(game="CS2")
        )
        assert result.game == "CS2"

    async def test_delete_game(self, uow: FakeUnitOfWork) -> None:
        admin = make_admin_user(uow._store)
        game = CompanyGame.create("Dota2")
        uow._store.company_games[game.id] = game
        await DeleteCompanyGameUseCase(uow).execute(admin.id, game.id)
        assert game.id not in uow._store.company_games

    async def test_delete_missing_game(self, uow: FakeUnitOfWork) -> None:
        admin = make_admin_user(uow._store)
        with pytest.raises(EntityNotFoundError):
            await DeleteCompanyGameUseCase(uow).execute(admin.id, uuid4())


class TestSubscriptionPlanUseCases:
    async def test_create_plan_with_game(self, uow: FakeUnitOfWork) -> None:
        admin = make_admin_user(uow._store)
        game = CompanyGame.create("Minecraft")
        uow._store.company_games[game.id] = game
        dto = SubscriptionPlanCreateDTO(type="monthly", game_id=game.id)
        result = await CreateSubscriptionPlanUseCase(uow).execute(admin.id, dto)
        assert result.type == "monthly"

    async def test_create_plan_missing_game(self, uow: FakeUnitOfWork) -> None:
        admin = make_admin_user(uow._store)
        dto = SubscriptionPlanCreateDTO(type="monthly", game_id=uuid4())
        with pytest.raises(EntityNotFoundError):
            await CreateSubscriptionPlanUseCase(uow).execute(admin.id, dto)


class TestSubscriptionUseCases:
    async def test_create_subscription(self, uow: FakeUnitOfWork) -> None:
        admin = make_admin_user(uow._store)
        user = User.create("subuser", "sub@example.com", "hash")
        uow._store.users[user.id] = user
        dto = SubscriptionCreateDTO(user_id=user.id)
        result = await CreateSubscriptionUseCase(uow).execute(admin.id, dto)
        assert result.user_id == user.id

    async def test_list_own_subscriptions(self, uow: FakeUnitOfWork) -> None:
        user = User.create("subuser", "sub@example.com", "hash")
        uow._store.users[user.id] = user
        dto = SubscriptionCreateDTO(user_id=user.id)
        admin = make_admin_user(uow._store)
        await CreateSubscriptionUseCase(uow).execute(admin.id, dto)
        subs = await ListSubscriptionsUseCase(uow).execute(user.id)
        assert len(subs) == 1

    async def test_list_other_user_subscriptions_forbidden(self, uow: FakeUnitOfWork) -> None:
        user = User.create("subuser", "sub@example.com", "hash")
        other = User.create("other", "other@example.com", "hash")
        uow._store.users[user.id] = user
        uow._store.users[other.id] = other
        with pytest.raises(AuthorizationError):
            await ListSubscriptionsUseCase(uow).execute(user.id, other.id)


class TestPromocodeUseCases:
    async def test_create_promocode(self, uow: FakeUnitOfWork) -> None:
        admin = make_admin_user(uow._store)
        plan = SubscriptionPlan.create("monthly")
        uow._store.subscription_plans[plan.id] = plan
        dto = PromocodeCreateDTO(code="SAVE10", plan_id=plan.id)
        result = await CreatePromocodeUseCase(uow).execute(admin.id, dto)
        assert result.code == "SAVE10"


class TestPaymentUseCases:
    async def test_create_payment_idempotent(self, uow: FakeUnitOfWork) -> None:
        user = User.create("payuser", "pay@example.com", "hash")
        plan = SubscriptionPlan.create("monthly")
        uow._store.users[user.id] = user
        uow._store.subscription_plans[plan.id] = plan
        dto = PaymentCreateDTO(
            user_id=user.id,
            plan_id=plan.id,
            amount=Decimal("100.00"),
            status="pending",
            robokassa_invoice_id="inv-1",
            idempotency_key="idem-1",
        )
        first = await CreatePaymentUseCase(uow).execute(dto)
        second = await CreatePaymentUseCase(uow).execute(dto)
        assert first.id == second.id

    async def test_create_payment_rejects_non_pending_status(self, uow: FakeUnitOfWork) -> None:
        user = User.create("payuser2", "pay2@example.com", "hash")
        plan = SubscriptionPlan.create("monthly")
        uow._store.users[user.id] = user
        uow._store.subscription_plans[plan.id] = plan
        dto = PaymentCreateDTO(
            user_id=user.id,
            plan_id=plan.id,
            amount=Decimal("100.00"),
            status="paid",
            robokassa_invoice_id="inv-2",
            idempotency_key="idem-2",
        )
        with pytest.raises(ValidationError):
            await CreatePaymentUseCase(uow).execute(dto)

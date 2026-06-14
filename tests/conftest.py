"""Pytest fixtures."""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import pytest
from dishka import Provider, Scope, make_async_container, provide
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from application.dtos import UserDTO
from application.use_cases import (
    CreateCompanyGameUseCase,
    CreatePaymentUseCase,
    CreatePromocodeUseCase,
    CreateRoleUseCase,
    CreateSubscriptionPlanUseCase,
    CreateSubscriptionUseCase,
    DeleteCompanyGameUseCase,
    GetCurrentUserUseCase,
    ListCompanyGamesUseCase,
    ListPaymentsUseCase,
    ListPromocodesUseCase,
    ListRolesUseCase,
    ListSubscriptionPlansUseCase,
    ListSubscriptionsUseCase,
    LoginUserUseCase,
    RegisterUserUseCase,
)
from config.security import create_access_token, hash_password
from domain.entities import (
    CompanyGame,
    Payment,
    PromocodeEntity,
    Role,
    Subscription,
    SubscriptionPlan,
    User,
)
from infrastructure.db.base import Base
from infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from main import create_app


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


class InMemoryStore:
    """Simple in-memory storage for test repositories."""

    def __init__(self) -> None:
        self.roles: dict[UUID, Role] = {}
        self.users: dict[UUID, User] = {}
        self.company_games: dict[UUID, CompanyGame] = {}
        self.subscription_plans: dict[UUID, SubscriptionPlan] = {}
        self.subscriptions: dict[UUID, Subscription] = {}
        self.promocodes: dict[UUID, PromocodeEntity] = {}
        self.payments: dict[UUID, Payment] = {}


class FakeRoleRepo:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def get_by_id(self, role_id: UUID) -> Role | None:
        return self._store.roles.get(role_id)

    async def get_by_name(self, name: str) -> Role | None:
        return next((r for r in self._store.roles.values() if r.role == name), None)

    async def list_all(self) -> list[Role]:
        return list(self._store.roles.values())

    async def add(self, entity: Role) -> Role:
        self._store.roles[entity.id] = entity
        return entity


class FakeUserRepo:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def get_by_id(self, user_id: UUID) -> User | None:
        return self._store.users.get(user_id)

    async def get_by_email(self, email: str) -> User | None:
        return next((u for u in self._store.users.values() if u.email == email), None)

    async def get_by_username(self, username: str) -> User | None:
        return next((u for u in self._store.users.values() if u.username == username), None)

    async def add(self, entity: User) -> User:
        self._store.users[entity.id] = entity
        return entity

    async def list_all(self) -> list[User]:
        return list(self._store.users.values())


class FakeCompanyGameRepo:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def get_by_id(self, game_id: UUID) -> CompanyGame | None:
        return self._store.company_games.get(game_id)

    async def get_by_name(self, name: str) -> CompanyGame | None:
        return next((g for g in self._store.company_games.values() if g.game == name), None)

    async def list_all(self) -> list[CompanyGame]:
        return list(self._store.company_games.values())

    async def add(self, entity: CompanyGame) -> CompanyGame:
        self._store.company_games[entity.id] = entity
        return entity

    async def delete(self, game_id: UUID) -> None:
        self._store.company_games.pop(game_id, None)


class FakeSubscriptionPlanRepo:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def get_by_id(self, plan_id: UUID) -> SubscriptionPlan | None:
        return self._store.subscription_plans.get(plan_id)

    async def list_all(self) -> list[SubscriptionPlan]:
        return list(self._store.subscription_plans.values())

    async def add(self, entity: SubscriptionPlan) -> SubscriptionPlan:
        self._store.subscription_plans[entity.id] = entity
        return entity

    async def delete(self, plan_id: UUID) -> None:
        self._store.subscription_plans.pop(plan_id, None)


class FakeSubscriptionRepo:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def get_by_id(self, subscription_id: UUID) -> Subscription | None:
        return self._store.subscriptions.get(subscription_id)

    async def get_by_user(self, user_id: UUID) -> list[Subscription]:
        return [s for s in self._store.subscriptions.values() if s.user_id == user_id]

    async def add(self, entity: Subscription) -> Subscription:
        self._store.subscriptions[entity.id] = entity
        return entity

    async def delete(self, subscription_id: UUID) -> None:
        self._store.subscriptions.pop(subscription_id, None)


class FakePromocodeRepo:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def get_by_id(self, promocode_id: UUID) -> PromocodeEntity | None:
        return self._store.promocodes.get(promocode_id)

    async def get_by_code(self, code: str) -> PromocodeEntity | None:
        return next(
            (p for p in self._store.promocodes.values() if p.code == code.upper()),
            None,
        )

    async def list_all(self) -> list[PromocodeEntity]:
        return list(self._store.promocodes.values())

    async def add(self, entity: PromocodeEntity) -> PromocodeEntity:
        self._store.promocodes[entity.id] = entity
        return entity

    async def delete(self, promocode_id: UUID) -> None:
        self._store.promocodes.pop(promocode_id, None)


class FakePaymentRepo:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def get_by_id(self, payment_id: UUID) -> Payment | None:
        return self._store.payments.get(payment_id)

    async def get_by_idempotency_key(self, key: str) -> Payment | None:
        return next(
            (p for p in self._store.payments.values() if p.idempotency_key == key),
            None,
        )

    async def list_by_user(self, user_id: UUID) -> list[Payment]:
        return [p for p in self._store.payments.values() if p.user_id == user_id]

    async def add(self, entity: Payment) -> Payment:
        self._store.payments[entity.id] = entity
        return entity


class FakePaymentEventRepo:
    async def add(self, entity):  # noqa: ANN001, ANN201
        return entity

    async def list_unprocessed(self) -> list:
        return []


class FakeUnitOfWork:
    """In-memory UoW for API and application tests."""

    def __init__(self, store: InMemoryStore | None = None) -> None:
        self._store = store or InMemoryStore()
        self.roles = FakeRoleRepo(self._store)
        self.users = FakeUserRepo(self._store)
        self.company_games = FakeCompanyGameRepo(self._store)
        self.subscription_plans = FakeSubscriptionPlanRepo(self._store)
        self.subscriptions = FakeSubscriptionRepo(self._store)
        self.promocodes = FakePromocodeRepo(self._store)
        self.payments = FakePaymentRepo(self._store)
        self.payment_events = FakePaymentEventRepo()
        self._committed = False

    async def __aenter__(self) -> FakeUnitOfWork:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:  # noqa: ANN001
        if exc_type is not None:
            self._committed = False

    async def commit(self) -> None:
        self._committed = True

    async def rollback(self) -> None:
        self._committed = False


class TestProvider(Provider):
    def __init__(self, uow: FakeUnitOfWork) -> None:
        super().__init__()
        self._uow = uow

    @provide(scope=Scope.REQUEST)
    def unit_of_work(self) -> FakeUnitOfWork:
        return self._uow

    @provide(scope=Scope.REQUEST)
    def register_user(self) -> RegisterUserUseCase:
        return RegisterUserUseCase(self._uow)

    @provide(scope=Scope.REQUEST)
    def login_user(self) -> LoginUserUseCase:
        return LoginUserUseCase(self._uow)

    @provide(scope=Scope.REQUEST)
    def get_current_user(self) -> GetCurrentUserUseCase:
        return GetCurrentUserUseCase(self._uow)

    @provide(scope=Scope.REQUEST)
    def list_roles(self) -> ListRolesUseCase:
        return ListRolesUseCase(self._uow)

    @provide(scope=Scope.REQUEST)
    def create_role(self) -> CreateRoleUseCase:
        return CreateRoleUseCase(self._uow)

    @provide(scope=Scope.REQUEST)
    def list_company_games(self) -> ListCompanyGamesUseCase:
        return ListCompanyGamesUseCase(self._uow)

    @provide(scope=Scope.REQUEST)
    def create_company_game(self) -> CreateCompanyGameUseCase:
        return CreateCompanyGameUseCase(self._uow)

    @provide(scope=Scope.REQUEST)
    def delete_company_game(self) -> DeleteCompanyGameUseCase:
        return DeleteCompanyGameUseCase(self._uow)

    @provide(scope=Scope.REQUEST)
    def list_subscription_plans(self) -> ListSubscriptionPlansUseCase:
        return ListSubscriptionPlansUseCase(self._uow)

    @provide(scope=Scope.REQUEST)
    def create_subscription_plan(self) -> CreateSubscriptionPlanUseCase:
        return CreateSubscriptionPlanUseCase(self._uow)

    @provide(scope=Scope.REQUEST)
    def list_subscriptions(self) -> ListSubscriptionsUseCase:
        return ListSubscriptionsUseCase(self._uow)

    @provide(scope=Scope.REQUEST)
    def create_subscription(self) -> CreateSubscriptionUseCase:
        return CreateSubscriptionUseCase(self._uow)

    @provide(scope=Scope.REQUEST)
    def list_promocodes(self) -> ListPromocodesUseCase:
        return ListPromocodesUseCase(self._uow)

    @provide(scope=Scope.REQUEST)
    def create_promocode(self) -> CreatePromocodeUseCase:
        return CreatePromocodeUseCase(self._uow)

    @provide(scope=Scope.REQUEST)
    def list_payments(self) -> ListPaymentsUseCase:
        return ListPaymentsUseCase(self._uow)

    @provide(scope=Scope.REQUEST)
    def create_payment(self) -> CreatePaymentUseCase:
        return CreatePaymentUseCase(self._uow)


@pytest.fixture
def fake_store() -> InMemoryStore:
    return InMemoryStore()


@pytest.fixture
def fake_uow(fake_store: InMemoryStore) -> FakeUnitOfWork:
    return FakeUnitOfWork(fake_store)


@pytest.fixture
async def client(fake_uow: FakeUnitOfWork) -> AsyncIterator[AsyncClient]:
    from dishka.integrations.fastapi import setup_dishka

    app = create_app()
    container = make_async_container(TestProvider(fake_uow))
    setup_dishka(container, app)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    await container.close()


@pytest.fixture
def sample_user(fake_store: InMemoryStore) -> User:
    user = User.create(
        username="testuser",
        email="test@example.com",
        password_hash=hash_password("password123"),
    )
    fake_store.users[user.id] = user
    return user


@pytest.fixture
def auth_headers(sample_user: User) -> dict[str, str]:
    token = create_access_token({"sub": str(sample_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """SQLite session for infrastructure integration tests."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def uow(db_session: AsyncSession) -> SqlAlchemyUnitOfWork:
    return SqlAlchemyUnitOfWork(db_session)

"""Pytest fixtures."""

from __future__ import annotations

import os

# Hermetic settings, applied before anything imports `config.settings` (which reads the
# environment once, at import). Env vars beat the developer's .env file, so tests never
# pick up real SMTP/Robokassa credentials or a local DATABASE_URL from it.
os.environ.update(
    {
        "ENV": "local",
        "DEBUG": "false",
        "SECRET_KEY": "test-secret-key-that-is-at-least-32-characters-long",
        # Replaced with the test container URL by the `database_url` fixture.
        "DATABASE_URL": "postgresql+asyncpg://unused:unused@127.0.0.1:1/unused",
        "SMTP_HOST": "",
        "SMTP_USERNAME": "",
        "SMTP_PASSWORD": "",
        "ROBOKASSA_MERCHANT_LOGIN": "",
        "ROBOKASSA_PASSWORD1": "",
        "ROBOKASSA_PASSWORD2": "",
        "BOOTSTRAP_ADMIN_USERNAME": "",
        "BOOTSTRAP_ADMIN_EMAIL": "",
        "BOOTSTRAP_ADMIN_PASSWORD": "",
    }
)

from collections.abc import AsyncIterator, Callable, Iterator  # noqa: E402
from datetime import date, datetime  # noqa: E402
from pathlib import Path  # noqa: E402
from uuid import UUID  # noqa: E402

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from dishka import Provider, Scope, make_async_container, provide  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool  # noqa: E402

from application.use_cases import (  # noqa: E402
    AuthenticateAccessTokenUseCase,
    ChangePasswordUseCase,
    CreateCompanyGameUseCase,
    CreatePaymentUseCase,
    CreatePromocodeUseCase,
    CreateRoleUseCase,
    CreateSubscriptionPlanUseCase,
    CreateSubscriptionUseCase,
    DeleteCompanyGameUseCase,
    DeletePromocodeUseCase,
    DeleteSubscriptionPlanUseCase,
    DeleteSubscriptionUseCase,
    GetCurrentUserUseCase,
    GetMaintenanceModeUseCase,
    GetPaymentUseCase,
    InitiatePaymentUseCase,
    ListCompanyGamesUseCase,
    ListPaymentsUseCase,
    ListPromocodesUseCase,
    ListRolesUseCase,
    ListSubscriptionPlansUseCase,
    ListSubscriptionsUseCase,
    ListUsersUseCase,
    LoginUserUseCase,
    LogoutUseCase,
    ProcessRobokassaWebhookUseCase,
    RefreshTokensUseCase,
    RegisterUserUseCase,
    ResendVerificationCodeUseCase,
    SetMaintenanceModeUseCase,
    UpdateCompanyGameUseCase,
    UpdatePromocodeUseCase,
    UpdateSubscriptionPlanUseCase,
    UpdateSubscriptionUseCase,
    UpdateUserUseCase,
    VerifyEmailUseCase,
)
from config.security import create_access_token  # noqa: E402
from config.settings import settings  # noqa: E402
from domain.entities import (  # noqa: E402
    CompanyGame,
    Payment,
    PromocodeEntity,
    RefreshToken,
    Role,
    Subscription,
    SubscriptionPlan,
    SystemSettings,
    User,
)
from infrastructure.cache.maintenance_cache import MaintenanceModeCache  # noqa: E402
from infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork  # noqa: E402
from infrastructure.payments.robokassa import RobokassaClient  # noqa: E402
from infrastructure.security.passwords import PwdlibPasswordHasher  # noqa: E402
from main import create_app  # noqa: E402
from presentation.middleware import rate_limit  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
# Same major version as docker-compose and production.
POSTGRES_IMAGE = "postgres:16-alpine"


def make_test_password_hasher() -> PwdlibPasswordHasher:
    """Argon2 with the cheapest valid parameters: tests check behavior, not hash strength."""
    return PwdlibPasswordHasher(time_cost=1, memory_cost_kib=1024, parallelism=1, max_concurrency=4)


_TEST_PASSWORD_HASHER = make_test_password_hasher()


def hash_password(password: str) -> str:
    """Synchronous hashing helper for building fixtures."""
    return _TEST_PASSWORD_HASHER.hash_sync(password)


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
        self.refresh_tokens: dict[UUID, RefreshToken] = {}
        self.system_settings = SystemSettings(maintenance_mode=False)

        user_role = Role.create("user")
        admin_role = Role.create("admin")
        self.roles[user_role.id] = user_role
        self.roles[admin_role.id] = admin_role


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

    async def exists_with_role_id(self, role_id: UUID) -> bool:
        return any(user.role_id == role_id for user in self._store.users.values())

    async def update(self, entity: User) -> User:
        self._store.users[entity.id] = entity
        return entity


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

    async def update(self, entity: CompanyGame) -> CompanyGame:
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

    async def update(self, entity: SubscriptionPlan) -> SubscriptionPlan:
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

    async def get_current_by_user_and_plan(
        self, user_id: UUID, plan_id: UUID, on_date: date
    ) -> Subscription | None:
        candidates = [
            s
            for s in self._store.subscriptions.values()
            if s.user_id == user_id
            and s.plan_id == plan_id
            and (s.active_until is None or s.active_until >= on_date)
        ]
        if not candidates:
            return None
        permanent = next((s for s in candidates if s.active_until is None), None)
        if permanent is not None:
            return permanent
        return max(candidates, key=lambda s: s.active_until)

    async def add(self, entity: Subscription) -> Subscription:
        self._store.subscriptions[entity.id] = entity
        return entity

    async def update(self, entity: Subscription) -> Subscription:
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

    async def update(self, entity: PromocodeEntity) -> PromocodeEntity:
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

    async def get_by_robokassa_invoice_id(
        self, invoice_id: str, *, for_update: bool = False
    ) -> Payment | None:
        return next(
            (p for p in self._store.payments.values() if p.robokassa_invoice_id == invoice_id),
            None,
        )

    async def list_by_user(self, user_id: UUID) -> list[Payment]:
        return [p for p in self._store.payments.values() if p.user_id == user_id]

    async def add(self, entity: Payment) -> Payment:
        self._store.payments[entity.id] = entity
        return entity

    async def update(self, entity: Payment) -> Payment:
        self._store.payments[entity.id] = entity
        return entity


class FakePaymentEventRepo:
    def __init__(self) -> None:
        self.events: list = []

    async def add(self, entity):  # noqa: ANN001, ANN201
        self.events.append(entity)
        return entity

    async def list_unprocessed(self) -> list:
        return [event for event in self.events if not event.processed]

    async def mark_processed(self, event_id: UUID) -> None:
        for event in self.events:
            if event.id == event_id:
                event.processed = True


class FakeRefreshTokenRepo:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def add(self, entity: RefreshToken) -> RefreshToken:
        self._store.refresh_tokens[entity.id] = entity
        return entity

    async def get_by_hash(
        self, token_hash: str, *, for_update: bool = False
    ) -> RefreshToken | None:
        return next(
            (t for t in self._store.refresh_tokens.values() if t.token_hash == token_hash),
            None,
        )

    async def revoke(
        self, token_id: UUID, now: datetime, replaced_by_id: UUID | None = None
    ) -> bool:
        token = self._store.refresh_tokens.get(token_id)
        if token is None or token.revoked_at is not None:
            return False
        token.revoked_at = now
        token.replaced_by_id = replaced_by_id
        return True

    async def revoke_family(self, family_id: UUID, now: datetime) -> int:
        return self._revoke_where(lambda t: t.family_id == family_id, now)

    async def revoke_all_for_user(self, user_id: UUID, now: datetime) -> int:
        return self._revoke_where(lambda t: t.user_id == user_id, now)

    async def is_family_active(self, family_id: UUID) -> bool:
        return any(
            t.family_id == family_id and t.revoked_at is None
            for t in self._store.refresh_tokens.values()
        )

    def _revoke_where(self, predicate: Callable[[RefreshToken], bool], now: datetime) -> int:
        revoked = 0
        for token in self._store.refresh_tokens.values():
            if token.revoked_at is None and predicate(token):
                token.revoked_at = now
                revoked += 1
        return revoked


class FakeSystemSettingsRepo:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def get(self) -> SystemSettings:
        return self._store.system_settings

    async def set_maintenance_mode(self, enabled: bool) -> SystemSettings:
        self._store.system_settings = SystemSettings(maintenance_mode=enabled)
        return self._store.system_settings


class FakeEmailSender:
    """Captures sent verification codes instead of talking to real SMTP."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    async def send_verification_code(self, *, to_email: str, code: str) -> None:
        self.sent.append((to_email, code))


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
        self.refresh_tokens = FakeRefreshTokenRepo(self._store)
        self.system_settings = FakeSystemSettingsRepo(self._store)
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
    def __init__(self, uow: FakeUnitOfWork, email_sender: FakeEmailSender | None = None) -> None:
        super().__init__()
        self._uow = uow
        self._email_sender = email_sender or FakeEmailSender()
        self._password_hasher = make_test_password_hasher()
        self._robokassa = RobokassaClient(
            merchant_login=settings.ROBOKASSA_MERCHANT_LOGIN or "test_merchant",
            password1=settings.ROBOKASSA_PASSWORD1 or "password1",
            password2=settings.ROBOKASSA_PASSWORD2 or "password2",
            is_test=True,
        )

    @provide(scope=Scope.REQUEST)
    def unit_of_work(self) -> FakeUnitOfWork:
        return self._uow

    @provide(scope=Scope.REQUEST)
    def register_user(self) -> RegisterUserUseCase:
        return RegisterUserUseCase(self._uow, self._email_sender, self._password_hasher)

    @provide(scope=Scope.REQUEST)
    def login_user(self) -> LoginUserUseCase:
        return LoginUserUseCase(self._uow, self._password_hasher)

    @provide(scope=Scope.REQUEST)
    def authenticate_access_token(self) -> AuthenticateAccessTokenUseCase:
        return AuthenticateAccessTokenUseCase(self._uow)

    @provide(scope=Scope.REQUEST)
    def refresh_tokens(self) -> RefreshTokensUseCase:
        return RefreshTokensUseCase(self._uow)

    @provide(scope=Scope.REQUEST)
    def logout(self) -> LogoutUseCase:
        return LogoutUseCase(self._uow)

    @provide(scope=Scope.REQUEST)
    def change_password(self) -> ChangePasswordUseCase:
        return ChangePasswordUseCase(self._uow, self._password_hasher)

    @provide(scope=Scope.REQUEST)
    def verify_email(self) -> VerifyEmailUseCase:
        return VerifyEmailUseCase(self._uow)

    @provide(scope=Scope.REQUEST)
    def resend_verification_code(self) -> ResendVerificationCodeUseCase:
        return ResendVerificationCodeUseCase(self._uow, self._email_sender)

    @provide(scope=Scope.REQUEST)
    def get_current_user(self) -> GetCurrentUserUseCase:
        return GetCurrentUserUseCase(self._uow)

    @provide(scope=Scope.REQUEST)
    def list_users(self) -> ListUsersUseCase:
        return ListUsersUseCase(self._uow)

    @provide(scope=Scope.REQUEST)
    def update_user(self) -> UpdateUserUseCase:
        return UpdateUserUseCase(self._uow)

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
    def update_company_game(self) -> UpdateCompanyGameUseCase:
        return UpdateCompanyGameUseCase(self._uow)

    @provide(scope=Scope.REQUEST)
    def list_subscription_plans(self) -> ListSubscriptionPlansUseCase:
        return ListSubscriptionPlansUseCase(self._uow)

    @provide(scope=Scope.REQUEST)
    def create_subscription_plan(self) -> CreateSubscriptionPlanUseCase:
        return CreateSubscriptionPlanUseCase(self._uow)

    @provide(scope=Scope.REQUEST)
    def update_subscription_plan(self) -> UpdateSubscriptionPlanUseCase:
        return UpdateSubscriptionPlanUseCase(self._uow)

    @provide(scope=Scope.REQUEST)
    def delete_subscription_plan(self) -> DeleteSubscriptionPlanUseCase:
        return DeleteSubscriptionPlanUseCase(self._uow)

    @provide(scope=Scope.REQUEST)
    def list_subscriptions(self) -> ListSubscriptionsUseCase:
        return ListSubscriptionsUseCase(self._uow)

    @provide(scope=Scope.REQUEST)
    def create_subscription(self) -> CreateSubscriptionUseCase:
        return CreateSubscriptionUseCase(self._uow)

    @provide(scope=Scope.REQUEST)
    def update_subscription(self) -> UpdateSubscriptionUseCase:
        return UpdateSubscriptionUseCase(self._uow)

    @provide(scope=Scope.REQUEST)
    def delete_subscription(self) -> DeleteSubscriptionUseCase:
        return DeleteSubscriptionUseCase(self._uow)

    @provide(scope=Scope.REQUEST)
    def list_promocodes(self) -> ListPromocodesUseCase:
        return ListPromocodesUseCase(self._uow)

    @provide(scope=Scope.REQUEST)
    def create_promocode(self) -> CreatePromocodeUseCase:
        return CreatePromocodeUseCase(self._uow)

    @provide(scope=Scope.REQUEST)
    def update_promocode(self) -> UpdatePromocodeUseCase:
        return UpdatePromocodeUseCase(self._uow)

    @provide(scope=Scope.REQUEST)
    def delete_promocode(self) -> DeletePromocodeUseCase:
        return DeletePromocodeUseCase(self._uow)

    @provide(scope=Scope.REQUEST)
    def list_payments(self) -> ListPaymentsUseCase:
        return ListPaymentsUseCase(self._uow)

    @provide(scope=Scope.REQUEST)
    def create_payment(self) -> CreatePaymentUseCase:
        return CreatePaymentUseCase(self._uow)

    @provide(scope=Scope.REQUEST)
    def initiate_payment(self) -> InitiatePaymentUseCase:
        return InitiatePaymentUseCase(self._uow, self._robokassa)

    @provide(scope=Scope.REQUEST)
    def get_payment(self) -> GetPaymentUseCase:
        return GetPaymentUseCase(self._uow)

    @provide(scope=Scope.REQUEST)
    def process_robokassa_webhook(self) -> ProcessRobokassaWebhookUseCase:
        return ProcessRobokassaWebhookUseCase(self._uow, self._robokassa)

    @provide(scope=Scope.REQUEST)
    def get_maintenance_mode(self) -> GetMaintenanceModeUseCase:
        return GetMaintenanceModeUseCase(self._uow)

    @provide(scope=Scope.REQUEST)
    def set_maintenance_mode(self) -> SetMaintenanceModeUseCase:
        return SetMaintenanceModeUseCase(self._uow)


@pytest.fixture
def fake_store() -> InMemoryStore:
    return InMemoryStore()


@pytest.fixture
def fake_uow(fake_store: InMemoryStore) -> FakeUnitOfWork:
    return FakeUnitOfWork(fake_store)


@pytest.fixture
def fake_email_sender() -> FakeEmailSender:
    return FakeEmailSender()


@pytest.fixture
async def client(
    database_url: str, fake_uow: FakeUnitOfWork, fake_email_sender: FakeEmailSender
) -> AsyncIterator[AsyncClient]:
    # `database_url` is requested for its side effect: MaintenanceMiddleware reads the
    # maintenance flag straight from PostgreSQL, outside the faked Unit of Work.
    from dishka.integrations.fastapi import setup_dishka

    app = create_app()
    container = make_async_container(TestProvider(fake_uow, fake_email_sender))
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


def make_admin_user(store: InMemoryStore) -> User:
    """Create an admin user in the in-memory test store."""
    admin_role = next(role for role in store.roles.values() if role.role == "admin")
    user = User.create(
        username="adminuser",
        email="admin@example.com",
        password_hash=hash_password("password123"),
        role_id=admin_role.id,
    )
    store.users[user.id] = user
    return user


@pytest.fixture
def admin_user(fake_store: InMemoryStore) -> User:
    return make_admin_user(fake_store)


@pytest.fixture
def admin_headers(admin_user: User) -> dict[str, str]:
    token = create_access_token({"sub": str(admin_user.id)})
    return {"Authorization": f"Bearer {token}"}


def _migrate(database_url: str) -> None:
    """Build the schema with the real Alembic migrations, not metadata.create_all().

    This way every test run also proves the migration chain applies cleanly. The Config
    is created without an ini file on purpose: env.py would otherwise call fileConfig(),
    which silences every logger configured before it (and breaks caplog).
    """
    settings.DATABASE_URL = database_url
    config = Config()
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    command.upgrade(config, "head")


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    """A migrated PostgreSQL for the whole test session.

    Uses ``TEST_DATABASE_URL`` when set (an already running server, e.g. a CI service
    container); otherwise starts a disposable container with testcontainers.
    """
    external_url = os.environ.get("TEST_DATABASE_URL")
    if external_url:
        _migrate(external_url)
        yield external_url
        return

    from testcontainers.community.postgres import PostgresContainer

    with PostgresContainer(POSTGRES_IMAGE, driver="asyncpg") as postgres:
        url = postgres.get_connection_url()
        _migrate(url)
        yield url


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Mark every test that (transitively) needs the database as `integration`.

    `pytest -m "not integration"` then runs the fast suite with no Docker at all.
    """
    for item in items:
        if "database_url" in getattr(item, "fixturenames", ()):
            item.add_marker(pytest.mark.integration)


@pytest.fixture(autouse=True)
def _reset_process_state() -> Iterator[None]:
    """Process-global caches must not leak between tests."""
    rate_limit._rate_limiter._requests.clear()
    MaintenanceModeCache.invalidate()
    yield
    rate_limit._rate_limiter._requests.clear()
    MaintenanceModeCache.invalidate()


@pytest.fixture
async def db_engine(database_url: str) -> AsyncIterator[AsyncEngine]:
    # NullPool: every test runs on its own event loop, and a pooled asyncpg connection
    # cannot be reused across loops.
    engine = create_async_engine(database_url, poolclass=NullPool)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """A session whose work is rolled back after the test, commits included.

    The session joins an outer transaction and turns its own commit() calls into
    SAVEPOINT releases, so the code under test commits for real while the test still
    leaves the database untouched.
    """
    async with db_engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(
            bind=connection,
            join_transaction_mode="create_savepoint",
            expire_on_commit=False,
        )
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()


@pytest.fixture
def pg_uow(db_session: AsyncSession) -> SqlAlchemyUnitOfWork:
    return SqlAlchemyUnitOfWork(db_session)


@pytest.fixture
def committing_session_factory(db_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Sessions that really commit — for tests that need several connections to see the
    same rows (e.g. lock contention). Such tests must clean up after themselves."""
    return async_sessionmaker(db_engine, expire_on_commit=False)

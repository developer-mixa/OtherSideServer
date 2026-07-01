"""Bootstrap admin user tests."""

from config.security import hash_password, verify_password
from domain.entities import User
from tests.conftest import FakeUnitOfWork, InMemoryStore

from application.bootstrap import bootstrap_admin_user
from config import settings


class _SessionContext:
    def __init__(self, session: object) -> None:
        self._session = session

    async def __aenter__(self) -> object:
        return self._session

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None


class _SessionFactory:
    def __init__(self, session: object) -> None:
        self._session = session

    def __call__(self) -> _SessionContext:
        return _SessionContext(self._session)


def _patch_sqlalchemy_uow(monkeypatch, uow: FakeUnitOfWork) -> None:
    import application.bootstrap as bootstrap_module

    class _FakeSqlUow:
        def __init__(self, _session: object) -> None:
            self.roles = uow.roles
            self.users = uow.users
            self._inner = uow

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
            return None

        async def commit(self) -> None:
            await self._inner.commit()

    monkeypatch.setattr(bootstrap_module, "SqlAlchemyUnitOfWork", _FakeSqlUow)


class TestBootstrapAdminUser:
    async def test_creates_admin_when_missing(self, monkeypatch) -> None:
        store = InMemoryStore()
        uow = FakeUnitOfWork(store)

        monkeypatch.setattr(settings.settings, "BOOTSTRAP_ADMIN_USERNAME", "bootstrapadmin")
        monkeypatch.setattr(settings.settings, "BOOTSTRAP_ADMIN_EMAIL", "bootstrap@example.com")
        monkeypatch.setattr(settings.settings, "BOOTSTRAP_ADMIN_PASSWORD", "securepassword12")
        _patch_sqlalchemy_uow(monkeypatch, uow)

        await bootstrap_admin_user(_SessionFactory(object()))

        admin_role = await uow.roles.get_by_name("admin")
        assert admin_role is not None
        created = await uow.users.get_by_email("bootstrap@example.com")
        assert created is not None
        assert created.role_id == admin_role.id
        assert verify_password("securepassword12", created.password_hash)

    async def test_skips_when_admin_exists(self, monkeypatch) -> None:
        store = InMemoryStore()
        uow = FakeUnitOfWork(store)
        admin_role = await uow.roles.get_by_name("admin")
        assert admin_role is not None
        existing = User.create(
            "existing",
            "existing@example.com",
            hash_password("securepassword12"),
            role_id=admin_role.id,
        )
        store.users[existing.id] = existing

        monkeypatch.setattr(settings.settings, "BOOTSTRAP_ADMIN_USERNAME", "bootstrapadmin")
        monkeypatch.setattr(settings.settings, "BOOTSTRAP_ADMIN_EMAIL", "bootstrap@example.com")
        monkeypatch.setattr(settings.settings, "BOOTSTRAP_ADMIN_PASSWORD", "securepassword12")
        _patch_sqlalchemy_uow(monkeypatch, uow)

        await bootstrap_admin_user(_SessionFactory(object()))

        assert len(store.users) == 1

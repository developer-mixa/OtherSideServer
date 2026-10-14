"""Login, refresh token rotation, logout and password change use case tests."""

from datetime import datetime, timedelta, timezone

import bcrypt
import pytest
from tests.conftest import FakeUnitOfWork, hash_password, make_admin_user, make_test_password_hasher

from application.dtos import AuthTokenDTO, UserUpdateDTO
from application.use_cases import (
    AuthenticateAccessTokenUseCase,
    ChangePasswordUseCase,
    LoginUserUseCase,
    LogoutUseCase,
    RefreshTokensUseCase,
    UpdateUserUseCase,
)
from config.security import (
    create_access_token,
    decode_access_token,
    get_user_id_from_token,
    hash_refresh_token,
)
from config.settings import settings
from domain.entities import RefreshToken, User
from domain.exceptions import (
    AuthenticationError,
    AuthorizationError,
    EntityNotFoundError,
    ValidationError,
)


@pytest.fixture
def uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def user(uow: FakeUnitOfWork) -> User:
    user = User.create(
        "sessionuser", "session@example.com", hash_password("password123"), is_verified=True
    )
    uow._store.users[user.id] = user
    return user


def _stored_token(uow: FakeUnitOfWork, raw_token: str) -> RefreshToken:
    token_hash = hash_refresh_token(raw_token)
    return next(t for t in uow._store.refresh_tokens.values() if t.token_hash == token_hash)


async def _login(uow: FakeUnitOfWork) -> AuthTokenDTO:
    return await LoginUserUseCase(uow, make_test_password_hasher()).execute(
        "session@example.com", "password123"
    )


class TestLoginIssuesSession:
    async def test_login_returns_access_and_refresh_tokens(
        self, uow: FakeUnitOfWork, user: User
    ) -> None:
        result = await _login(uow)

        assert get_user_id_from_token(result.access_token) == user.id
        assert result.expires_in == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        stored = _stored_token(uow, result.refresh_token)
        assert stored.user_id == user.id
        assert stored.family_id == stored.id
        assert stored.revoked_at is None
        assert stored.token_hash != result.refresh_token
        assert uow._committed is True

    async def test_each_login_starts_its_own_family(self, uow: FakeUnitOfWork, user: User) -> None:
        first, second = await _login(uow), await _login(uow)
        assert (
            _stored_token(uow, first.refresh_token).family_id
            != _stored_token(uow, second.refresh_token).family_id
        )

    async def test_login_upgrades_legacy_bcrypt_hash(self, uow: FakeUnitOfWork, user: User) -> None:
        user.password_hash = bcrypt.hashpw(b"password123", bcrypt.gensalt(rounds=4)).decode()

        await _login(uow)

        assert uow._store.users[user.id].password_hash.startswith("$argon2id$")

    async def test_login_keeps_current_argon2_hash(self, uow: FakeUnitOfWork, user: User) -> None:
        original = user.password_hash
        await _login(uow)
        assert uow._store.users[user.id].password_hash == original

    async def test_failed_login_does_not_upgrade_hash(
        self, uow: FakeUnitOfWork, user: User
    ) -> None:
        legacy = bcrypt.hashpw(b"password123", bcrypt.gensalt(rounds=4)).decode()
        user.password_hash = legacy
        with pytest.raises(AuthenticationError):
            await LoginUserUseCase(uow, make_test_password_hasher()).execute(
                "session@example.com", "wrong-password"
            )
        assert uow._store.users[user.id].password_hash == legacy

    async def test_unknown_email_runs_dummy_verify(self, uow: FakeUnitOfWork) -> None:
        calls: list[str] = []

        class _SpyHasher:
            async def hash(self, password: str) -> str:
                raise AssertionError("not expected")

            async def verify(self, password: str, password_hash: str):  # noqa: ANN201
                raise AssertionError("not expected")

            async def dummy_verify(self, password: str) -> None:
                calls.append(password)

        with pytest.raises(AuthenticationError):
            await LoginUserUseCase(uow, _SpyHasher()).execute("nobody@example.com", "secret123")
        assert calls == ["secret123"]
        assert uow._store.refresh_tokens == {}


class TestRefreshTokensUseCase:
    async def test_rotation_issues_new_pair_and_revokes_old(
        self, uow: FakeUnitOfWork, user: User
    ) -> None:
        login = await _login(uow)

        refreshed = await RefreshTokensUseCase(uow).execute(login.refresh_token)

        old = _stored_token(uow, login.refresh_token)
        new = _stored_token(uow, refreshed.refresh_token)
        assert refreshed.refresh_token != login.refresh_token
        assert get_user_id_from_token(refreshed.access_token) == user.id
        assert old.revoked_at is not None
        assert old.replaced_by_id == new.id
        assert new.family_id == old.family_id
        assert new.revoked_at is None

    async def test_unknown_token_is_rejected(self, uow: FakeUnitOfWork) -> None:
        with pytest.raises(AuthenticationError) as exc_info:
            await RefreshTokensUseCase(uow).execute("not-a-real-token")
        assert exc_info.value.code == "refresh_token_invalid"

    async def test_reuse_of_rotated_token_revokes_the_whole_family(
        self, uow: FakeUnitOfWork, user: User
    ) -> None:
        login = await _login(uow)
        use_case = RefreshTokensUseCase(uow)
        second = await use_case.execute(login.refresh_token)
        third = await use_case.execute(second.refresh_token)

        # The first token is replayed (e.g. it was stolen before rotation).
        with pytest.raises(AuthenticationError) as exc_info:
            await use_case.execute(login.refresh_token)
        assert exc_info.value.code == "refresh_token_reused"

        # The newest legitimate token is dead too, so the thief's chain cannot continue.
        assert _stored_token(uow, third.refresh_token).revoked_at is not None
        with pytest.raises(AuthenticationError) as exc_info:
            await use_case.execute(third.refresh_token)
        assert exc_info.value.code == "refresh_token_reused"

    async def test_reuse_detection_leaves_other_sessions_alone(
        self, uow: FakeUnitOfWork, user: User
    ) -> None:
        phone, laptop = await _login(uow), await _login(uow)
        use_case = RefreshTokensUseCase(uow)
        await use_case.execute(phone.refresh_token)

        with pytest.raises(AuthenticationError):
            await use_case.execute(phone.refresh_token)

        assert _stored_token(uow, laptop.refresh_token).revoked_at is None
        await use_case.execute(laptop.refresh_token)

    async def test_expired_token_is_rejected(self, uow: FakeUnitOfWork, user: User) -> None:
        login = await _login(uow)
        _stored_token(uow, login.refresh_token).expires_at = datetime.now(timezone.utc) - timedelta(
            seconds=1
        )

        with pytest.raises(AuthenticationError) as exc_info:
            await RefreshTokensUseCase(uow).execute(login.refresh_token)
        assert exc_info.value.code == "refresh_token_expired"

    async def test_blocked_user_cannot_refresh_and_session_is_revoked(
        self, uow: FakeUnitOfWork, user: User
    ) -> None:
        login = await _login(uow)
        user.is_blocked = True

        with pytest.raises(AuthorizationError) as exc_info:
            await RefreshTokensUseCase(uow).execute(login.refresh_token)
        assert exc_info.value.code == "user_blocked"
        assert _stored_token(uow, login.refresh_token).revoked_at is not None

    async def test_deleted_user_cannot_refresh(self, uow: FakeUnitOfWork, user: User) -> None:
        login = await _login(uow)
        del uow._store.users[user.id]

        with pytest.raises(AuthenticationError) as exc_info:
            await RefreshTokensUseCase(uow).execute(login.refresh_token)
        assert exc_info.value.code == "refresh_token_invalid"


class TestLogoutUseCase:
    async def test_logout_revokes_the_session_family(self, uow: FakeUnitOfWork, user: User) -> None:
        login = await _login(uow)
        rotated = await RefreshTokensUseCase(uow).execute(login.refresh_token)

        await LogoutUseCase(uow).execute(rotated.refresh_token)

        assert _stored_token(uow, rotated.refresh_token).revoked_at is not None
        with pytest.raises(AuthenticationError):
            await RefreshTokensUseCase(uow).execute(rotated.refresh_token)

    async def test_logout_keeps_other_sessions(self, uow: FakeUnitOfWork, user: User) -> None:
        phone, laptop = await _login(uow), await _login(uow)
        await LogoutUseCase(uow).execute(phone.refresh_token)
        assert _stored_token(uow, laptop.refresh_token).revoked_at is None

    async def test_logout_with_unknown_token_is_a_no_op(self, uow: FakeUnitOfWork) -> None:
        await LogoutUseCase(uow).execute("not-a-real-token")

    async def test_logout_is_idempotent(self, uow: FakeUnitOfWork, user: User) -> None:
        login = await _login(uow)
        await LogoutUseCase(uow).execute(login.refresh_token)
        await LogoutUseCase(uow).execute(login.refresh_token)


class TestChangePasswordUseCase:
    async def test_changes_password_and_revokes_every_session(
        self, uow: FakeUnitOfWork, user: User
    ) -> None:
        phone, laptop = await _login(uow), await _login(uow)
        hasher = make_test_password_hasher()

        await ChangePasswordUseCase(uow, hasher).execute(user.id, "password123", "new-password-1")

        stored = uow._store.users[user.id]
        assert (await hasher.verify("new-password-1", stored.password_hash)).is_valid
        assert not (await hasher.verify("password123", stored.password_hash)).is_valid
        assert _stored_token(uow, phone.refresh_token).revoked_at is not None
        assert _stored_token(uow, laptop.refresh_token).revoked_at is not None

    async def test_wrong_current_password_is_rejected(
        self, uow: FakeUnitOfWork, user: User
    ) -> None:
        login = await _login(uow)
        with pytest.raises(ValidationError) as exc_info:
            await ChangePasswordUseCase(uow, make_test_password_hasher()).execute(
                user.id, "wrong-password", "new-password-1"
            )
        assert exc_info.value.code == "current_password_invalid"
        assert _stored_token(uow, login.refresh_token).revoked_at is None

    async def test_new_password_must_be_valid(self, uow: FakeUnitOfWork, user: User) -> None:
        with pytest.raises(ValidationError) as exc_info:
            await ChangePasswordUseCase(uow, make_test_password_hasher()).execute(
                user.id, "password123", "short"
            )
        assert exc_info.value.code == "password_too_short"

    async def test_new_password_must_differ(self, uow: FakeUnitOfWork, user: User) -> None:
        with pytest.raises(ValidationError) as exc_info:
            await ChangePasswordUseCase(uow, make_test_password_hasher()).execute(
                user.id, "password123", "password123"
            )
        assert exc_info.value.code == "password_unchanged"

    async def test_blocked_user_is_rejected(self, uow: FakeUnitOfWork, user: User) -> None:
        user.is_blocked = True
        with pytest.raises(AuthorizationError):
            await ChangePasswordUseCase(uow, make_test_password_hasher()).execute(
                user.id, "password123", "new-password-1"
            )

    async def test_unknown_user(self, uow: FakeUnitOfWork, user: User) -> None:
        del uow._store.users[user.id]
        with pytest.raises(EntityNotFoundError):
            await ChangePasswordUseCase(uow, make_test_password_hasher()).execute(
                user.id, "password123", "new-password-1"
            )


class TestBlockingRevokesSessions:
    async def test_admin_block_revokes_refresh_tokens(
        self, uow: FakeUnitOfWork, user: User
    ) -> None:
        admin = make_admin_user(uow._store)
        login = await _login(uow)

        await UpdateUserUseCase(uow).execute(admin.id, user.id, UserUpdateDTO(is_blocked=True))

        assert _stored_token(uow, login.refresh_token).revoked_at is not None

    async def test_unrelated_update_keeps_sessions(self, uow: FakeUnitOfWork, user: User) -> None:
        admin = make_admin_user(uow._store)
        login = await _login(uow)

        await UpdateUserUseCase(uow).execute(admin.id, user.id, UserUpdateDTO(is_verified=True))

        assert _stored_token(uow, login.refresh_token).revoked_at is None


class TestAuthenticateAccessTokenUseCase:
    async def _authenticate(self, uow: FakeUnitOfWork, access_token: str | None):  # noqa: ANN202
        return await AuthenticateAccessTokenUseCase(uow).execute(access_token)

    async def test_access_token_is_bound_to_its_session(
        self, uow: FakeUnitOfWork, user: User
    ) -> None:
        login = await _login(uow)
        claims = decode_access_token(login.access_token)
        assert claims["sid"] == str(_stored_token(uow, login.refresh_token).family_id)
        assert await self._authenticate(uow, login.access_token) == user.id

    async def test_logout_revokes_access_token_immediately(
        self, uow: FakeUnitOfWork, user: User
    ) -> None:
        login = await _login(uow)
        await LogoutUseCase(uow).execute(login.refresh_token)

        with pytest.raises(AuthenticationError) as exc_info:
            await self._authenticate(uow, login.access_token)
        assert exc_info.value.code == "session_revoked"

    async def test_logout_leaves_other_sessions_access_tokens_valid(
        self, uow: FakeUnitOfWork, user: User
    ) -> None:
        phone, laptop = await _login(uow), await _login(uow)
        await LogoutUseCase(uow).execute(phone.refresh_token)
        assert await self._authenticate(uow, laptop.access_token) == user.id

    async def test_rotation_keeps_earlier_access_token_of_the_session_valid(
        self, uow: FakeUnitOfWork, user: User
    ) -> None:
        login = await _login(uow)
        await RefreshTokensUseCase(uow).execute(login.refresh_token)
        assert await self._authenticate(uow, login.access_token) == user.id

    async def test_reuse_detection_kills_access_tokens_of_the_session(
        self, uow: FakeUnitOfWork, user: User
    ) -> None:
        login = await _login(uow)
        rotated = await RefreshTokensUseCase(uow).execute(login.refresh_token)
        with pytest.raises(AuthenticationError):
            await RefreshTokensUseCase(uow).execute(login.refresh_token)

        for token in (login.access_token, rotated.access_token):
            with pytest.raises(AuthenticationError) as exc_info:
                await self._authenticate(uow, token)
            assert exc_info.value.code == "session_revoked"

    async def test_password_change_revokes_access_tokens_of_all_sessions(
        self, uow: FakeUnitOfWork, user: User
    ) -> None:
        phone, laptop = await _login(uow), await _login(uow)
        await ChangePasswordUseCase(uow, make_test_password_hasher()).execute(
            user.id, "password123", "new-password-1"
        )
        for token in (phone.access_token, laptop.access_token):
            with pytest.raises(AuthenticationError):
                await self._authenticate(uow, token)

    async def test_blocked_user_keeps_getting_user_blocked(
        self, uow: FakeUnitOfWork, user: User
    ) -> None:
        admin = make_admin_user(uow._store)
        login = await _login(uow)
        await UpdateUserUseCase(uow).execute(admin.id, user.id, UserUpdateDTO(is_blocked=True))

        with pytest.raises(AuthorizationError) as exc_info:
            await self._authenticate(uow, login.access_token)
        assert exc_info.value.code == "user_blocked"

    async def test_token_without_session_id_is_accepted_until_it_expires(
        self, uow: FakeUnitOfWork, user: User
    ) -> None:
        legacy = create_access_token({"sub": str(user.id)})
        assert await self._authenticate(uow, legacy) == user.id

    async def test_malformed_session_id_is_rejected(self, uow: FakeUnitOfWork, user: User) -> None:
        token = create_access_token({"sub": str(user.id), "sid": "not-a-uuid"})
        with pytest.raises(AuthenticationError) as exc_info:
            await self._authenticate(uow, token)
        assert exc_info.value.code == "token_invalid"

    async def test_missing_token(self, uow: FakeUnitOfWork) -> None:
        with pytest.raises(AuthenticationError) as exc_info:
            await self._authenticate(uow, None)
        assert exc_info.value.code == "not_authenticated"

    async def test_invalid_token(self, uow: FakeUnitOfWork) -> None:
        with pytest.raises(AuthenticationError) as exc_info:
            await self._authenticate(uow, "garbage")
        assert exc_info.value.code == "token_invalid"

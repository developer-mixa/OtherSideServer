"""Refresh token persistence and rotation against a real PostgreSQL (testcontainers)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from application.use_cases import RefreshTokensUseCase
from application.use_cases.sessions import issue_token_pair
from config.security import hash_refresh_token
from domain.entities import RefreshToken, User
from domain.exceptions import AuthenticationError
from infrastructure.db.models import RefreshTokenModel, UserModel
from infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork


def _new_user() -> User:
    suffix = uuid4().hex[:12]
    return User.create(f"rt-{suffix}", f"rt-{suffix}@example.com", "hash", is_verified=True)


def _issue(user: User, now: datetime, family_id=None) -> RefreshToken:  # noqa: ANN001
    return RefreshToken.issue(
        user_id=user.id,
        token_hash=hash_refresh_token(uuid4().hex),
        now=now,
        ttl=timedelta(days=1),
        family_id=family_id,
    )


async def _persist_user(uow: SqlAlchemyUnitOfWork) -> User:
    # Committed first, as in production (tokens are only issued for existing users):
    # without a relationship() between the models, the ORM does not know to INSERT the
    # user before a token that references it within one flush.
    user = _new_user()
    await uow.users.add(user)
    await uow.commit()
    return user


class TestSqlAlchemyRefreshTokenRepository:
    async def test_add_and_get_by_hash_round_trip(self, pg_uow: SqlAlchemyUnitOfWork) -> None:
        user = await _persist_user(pg_uow)
        token = _issue(user, datetime.now(timezone.utc))
        await pg_uow.refresh_tokens.add(token)
        await pg_uow.commit()

        loaded = await pg_uow.refresh_tokens.get_by_hash(token.token_hash, for_update=True)

        assert loaded == token
        assert await pg_uow.refresh_tokens.get_by_hash("0" * 64) is None

    async def test_revoke_is_conditional_on_token_being_live(
        self, pg_uow: SqlAlchemyUnitOfWork
    ) -> None:
        user = await _persist_user(pg_uow)
        now = datetime.now(timezone.utc)
        old, new = _issue(user, now), _issue(user, now)
        await pg_uow.refresh_tokens.add(old)
        await pg_uow.refresh_tokens.add(new)

        assert await pg_uow.refresh_tokens.revoke(old.id, now, replaced_by_id=new.id) is True
        assert await pg_uow.refresh_tokens.revoke(old.id, now + timedelta(hours=1)) is False

        loaded = await pg_uow.refresh_tokens.get_by_hash(old.token_hash)
        assert loaded is not None
        assert loaded.revoked_at == now
        assert loaded.replaced_by_id == new.id

    async def test_revoke_family_and_user_touch_only_live_matching_rows(
        self, pg_uow: SqlAlchemyUnitOfWork
    ) -> None:
        alice, bob = await _persist_user(pg_uow), await _persist_user(pg_uow)
        now = datetime.now(timezone.utc)
        session_a1 = _issue(alice, now)
        await pg_uow.refresh_tokens.add(session_a1)
        session_a1_next = _issue(alice, now, family_id=session_a1.family_id)
        await pg_uow.refresh_tokens.add(session_a1_next)
        session_a2 = _issue(alice, now)
        await pg_uow.refresh_tokens.add(session_a2)
        bob_session = _issue(bob, now)
        await pg_uow.refresh_tokens.add(bob_session)

        assert await pg_uow.refresh_tokens.revoke_family(session_a1.family_id, now) == 2
        assert await pg_uow.refresh_tokens.revoke_family(session_a1.family_id, now) == 0
        assert await pg_uow.refresh_tokens.revoke_all_for_user(alice.id, now) == 1

        bob_loaded = await pg_uow.refresh_tokens.get_by_hash(bob_session.token_hash)
        assert bob_loaded is not None
        assert bob_loaded.revoked_at is None

    async def test_is_family_active(self, pg_uow: SqlAlchemyUnitOfWork) -> None:
        user = await _persist_user(pg_uow)
        now = datetime.now(timezone.utc)
        first = _issue(user, now)
        await pg_uow.refresh_tokens.add(first)
        second = _issue(user, now, family_id=first.family_id)
        await pg_uow.refresh_tokens.add(second)

        await pg_uow.refresh_tokens.revoke(first.id, now, replaced_by_id=second.id)
        assert await pg_uow.refresh_tokens.is_family_active(first.family_id) is True

        await pg_uow.refresh_tokens.revoke_family(first.family_id, now)
        assert await pg_uow.refresh_tokens.is_family_active(first.family_id) is False
        assert await pg_uow.refresh_tokens.is_family_active(uuid4()) is False

    async def test_tokens_are_deleted_with_their_user(
        self, pg_uow: SqlAlchemyUnitOfWork, db_session: AsyncSession
    ) -> None:
        user = await _persist_user(pg_uow)
        token = _issue(user, datetime.now(timezone.utc))
        await pg_uow.refresh_tokens.add(token)
        await pg_uow.commit()

        await db_session.execute(delete(UserModel).where(UserModel.id == user.id))

        assert await pg_uow.refresh_tokens.get_by_hash(token.token_hash) is None


class TestRotationOnPostgres:
    async def test_rotation_and_reuse_detection(self, pg_uow: SqlAlchemyUnitOfWork) -> None:
        user = _new_user()
        await pg_uow.users.add(user)
        await pg_uow.commit()
        login, _ = await issue_token_pair(pg_uow, user.id, datetime.now(timezone.utc))
        await pg_uow.commit()
        use_case = RefreshTokensUseCase(pg_uow)

        rotated = await use_case.execute(login.refresh_token)
        with pytest.raises(AuthenticationError) as exc_info:
            await use_case.execute(login.refresh_token)

        assert exc_info.value.code == "refresh_token_reused"
        newest = await pg_uow.refresh_tokens.get_by_hash(hash_refresh_token(rotated.refresh_token))
        assert newest is not None
        assert newest.revoked_at is not None


@pytest.fixture
async def committed_session(
    committing_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[tuple[User, str]]:
    """A user with one live refresh token, really committed so other connections see it."""
    user = _new_user()
    async with committing_session_factory() as session:
        uow = SqlAlchemyUnitOfWork(session)
        await uow.users.add(user)
        await uow.commit()
        tokens, _ = await issue_token_pair(uow, user.id, datetime.now(timezone.utc))
        await uow.commit()
    try:
        yield user, tokens.refresh_token
    finally:
        async with committing_session_factory() as session:
            # Tokens go with the user (ON DELETE CASCADE).
            await session.execute(delete(UserModel).where(UserModel.id == user.id))
            await session.commit()


class TestConcurrentRefresh:
    async def test_parallel_refresh_with_same_token_lets_exactly_one_win(
        self,
        committing_session_factory: async_sessionmaker[AsyncSession],
        committed_session: tuple[User, str],
    ) -> None:
        user, raw_token = committed_session

        async def refresh() -> object:
            async with committing_session_factory() as session:
                try:
                    return await RefreshTokensUseCase(SqlAlchemyUnitOfWork(session)).execute(
                        raw_token
                    )
                except AuthenticationError as exc:
                    return exc

        results = await asyncio.gather(refresh(), refresh())

        errors = [r for r in results if isinstance(r, AuthenticationError)]
        assert len(errors) == 1
        assert errors[0].code == "refresh_token_reused"
        # Strict rotation: the duplicate looks like a replay, so the whole family —
        # including the token the "winner" just received — ends up revoked.
        async with committing_session_factory() as session:
            rows = (
                await session.execute(
                    select(RefreshTokenModel).where(RefreshTokenModel.user_id == user.id)
                )
            ).scalars()
            tokens = list(rows)
        assert len(tokens) == 2
        assert all(t.revoked_at is not None for t in tokens)

    async def test_refresh_waits_for_row_lock(
        self,
        committing_session_factory: async_sessionmaker[AsyncSession],
        committed_session: tuple[User, str],
    ) -> None:
        _, raw_token = committed_session

        async with committing_session_factory() as locker:
            await locker.execute(
                select(RefreshTokenModel)
                .where(RefreshTokenModel.token_hash == hash_refresh_token(raw_token))
                .with_for_update()
            )

            async def refresh() -> object:
                async with committing_session_factory() as session:
                    return await RefreshTokensUseCase(SqlAlchemyUnitOfWork(session)).execute(
                        raw_token
                    )

            task = asyncio.create_task(refresh())
            await asyncio.sleep(0.3)
            assert not task.done(), "refresh must block while another transaction holds the row"
            await locker.rollback()

        result = await asyncio.wait_for(task, timeout=10)
        assert getattr(result, "refresh_token", None)

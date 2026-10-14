"""Repository integration tests against a real PostgreSQL (testcontainers).

These exercise the `SqlAlchemy*Repository` classes directly (bypassing the fake in-memory
UoW used elsewhere), including the SQL `merge()` update path. Each test runs inside a
transaction that is rolled back afterwards — see the `pg_uow` fixture in conftest.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from domain.entities import CompanyGame, PromocodeEntity, Subscription, SubscriptionPlan, User
from infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


class TestUserRepositoryUpdate:
    async def test_update_persists_changes(self, pg_uow: SqlAlchemyUnitOfWork) -> None:
        user = User.create(_unique("user"), f"{_unique('user')}@example.com", "hash")
        await pg_uow.users.add(user)
        await pg_uow.commit()

        user.username = _unique("renamed")
        user.is_blocked = True
        await pg_uow.users.update(user)
        await pg_uow.commit()

        reloaded = await pg_uow.users.get_by_id(user.id)
        assert reloaded is not None
        assert reloaded.username == user.username
        assert reloaded.is_blocked is True


class TestCompanyGameRepositoryUpdate:
    async def test_update_persists_changes(self, pg_uow: SqlAlchemyUnitOfWork) -> None:
        game = CompanyGame.create(_unique("game"))
        await pg_uow.company_games.add(game)
        await pg_uow.commit()

        new_name = _unique("renamed-game")
        game.game = new_name
        await pg_uow.company_games.update(game)
        await pg_uow.commit()

        reloaded = await pg_uow.company_games.get_by_id(game.id)
        assert reloaded is not None
        assert reloaded.game == new_name


class TestSubscriptionPlanRepositoryUpdate:
    async def test_update_persists_changes(self, pg_uow: SqlAlchemyUnitOfWork) -> None:
        plan = SubscriptionPlan.create(_unique("monthly"), price_amount=Decimal("10.00"))
        await pg_uow.subscription_plans.add(plan)
        await pg_uow.commit()

        plan.type = _unique("yearly")
        plan.is_active = False
        await pg_uow.subscription_plans.update(plan)
        await pg_uow.commit()

        reloaded = await pg_uow.subscription_plans.get_by_id(plan.id)
        assert reloaded is not None
        assert reloaded.type == plan.type
        assert reloaded.is_active is False


class TestSubscriptionRepositoryUpdate:
    async def test_update_persists_changes(self, pg_uow: SqlAlchemyUnitOfWork) -> None:
        user = User.create(_unique("subowner"), f"{_unique('subowner')}@example.com", "hash")
        await pg_uow.users.add(user)
        plan = SubscriptionPlan.create(_unique("monthly"))
        await pg_uow.subscription_plans.add(plan)
        await pg_uow.commit()

        sub = Subscription.create(user_id=user.id)
        await pg_uow.subscriptions.add(sub)
        await pg_uow.commit()

        sub.plan_id = plan.id
        await pg_uow.subscriptions.update(sub)
        await pg_uow.commit()

        reloaded = await pg_uow.subscriptions.get_by_id(sub.id)
        assert reloaded is not None
        assert reloaded.plan_id == plan.id


class TestPromocodeRepositoryUpdate:
    async def test_update_persists_changes(self, pg_uow: SqlAlchemyUnitOfWork) -> None:
        plan = SubscriptionPlan.create(_unique("monthly"))
        await pg_uow.subscription_plans.add(plan)
        await pg_uow.commit()

        code = PromocodeEntity.create(_unique("SAVE"), plan.id)
        await pg_uow.promocodes.add(code)
        await pg_uow.commit()

        new_code = _unique("SAVE").upper()
        code.code = new_code
        code.is_active = False
        await pg_uow.promocodes.update(code)
        await pg_uow.commit()

        reloaded = await pg_uow.promocodes.get_by_id(code.id)
        assert reloaded is not None
        assert reloaded.code == new_code
        assert reloaded.is_active is False

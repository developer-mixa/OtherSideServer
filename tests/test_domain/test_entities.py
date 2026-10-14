"""Domain entity tests."""

from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from domain.entities import (
    CompanyGame,
    Payment,
    PromocodeEntity,
    Role,
    Subscription,
    SubscriptionPlan,
    User,
)


class TestRole:
    def test_create_role(self) -> None:
        role = Role.create("admin")
        assert role.role == "admin"
        assert role.id is not None


class TestUser:
    def test_create_user(self) -> None:
        user = User.create("john", "john@example.com", "hashed")
        assert user.username == "john"
        assert user.email == "john@example.com"
        assert user.is_verified is False


class TestSubscription:
    def test_is_active_when_future_date(self) -> None:
        sub = Subscription.create(
            user_id=uuid4(),
            active_until=date.today() + timedelta(days=30),
        )
        assert sub.is_active() is True

    def test_is_active_when_expired(self) -> None:
        sub = Subscription.create(
            user_id=uuid4(),
            active_until=date.today() - timedelta(days=1),
        )
        assert sub.is_active() is False

    def test_is_active_when_no_date(self) -> None:
        sub = Subscription.create(user_id=uuid4())
        assert sub.is_active() is True
        assert sub.is_permanent() is True


class TestPromocode:
    def test_create_uppercases_code(self) -> None:
        code = PromocodeEntity.create("save10", uuid4())
        assert code.code == "SAVE10"


class TestPayment:
    def test_create_payment(self) -> None:
        payment = Payment.create(
            user_id=uuid4(),
            plan_id=uuid4(),
            amount=Decimal("99.99"),
            status="pending",
            robokassa_invoice_id="inv-1",
            idempotency_key="key-1",
        )
        assert payment.amount == Decimal("99.99")
        assert payment.status == "pending"


class TestCompanyGame:
    def test_create_game(self) -> None:
        game = CompanyGame.create("Minecraft")
        assert game.game == "Minecraft"


class TestSubscriptionPlan:
    def test_create_plan(self) -> None:
        plan = SubscriptionPlan.create("monthly", uuid4())
        assert plan.type == "monthly"

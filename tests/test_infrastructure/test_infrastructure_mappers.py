"""Infrastructure mapper round-trip tests."""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from domain.entities import (
    CompanyGame,
    Payment,
    PaymentEvent,
    PromocodeEntity,
    Role,
    Subscription,
    SubscriptionPlan,
    User,
)
from infrastructure.mappers import (
    company_game_entity_to_model,
    company_game_model_to_entity,
    payment_entity_to_model,
    payment_event_entity_to_model,
    payment_event_model_to_entity,
    payment_model_to_entity,
    promocode_entity_to_model,
    promocode_model_to_entity,
    role_entity_to_model,
    role_model_to_entity,
    subscription_entity_to_model,
    subscription_model_to_entity,
    subscription_plan_entity_to_model,
    subscription_plan_model_to_entity,
    user_entity_to_model,
    user_model_to_entity,
)


class TestRoleMapper:
    def test_round_trip(self) -> None:
        entity = Role(id=uuid4(), role="admin")
        model = role_entity_to_model(entity)
        restored = role_model_to_entity(model)
        assert restored.id == entity.id
        assert restored.role == entity.role


class TestUserMapper:
    def test_round_trip(self) -> None:
        entity = User.create("john", "john@example.com", "hash", role_id=uuid4())
        model = user_entity_to_model(entity)
        restored = user_model_to_entity(model)
        assert restored.username == entity.username
        assert restored.email == entity.email
        assert restored.is_blocked == entity.is_blocked

    def test_round_trip_blocked(self) -> None:
        entity = User.create("blocked", "blocked@example.com", "hash", is_blocked=True)
        model = user_entity_to_model(entity)
        restored = user_model_to_entity(model)
        assert restored.is_blocked is True

    def test_round_trip_verification_fields(self) -> None:
        entity = User.create("pending", "pending@example.com", "hash")
        entity.verification_code_hash = "somehash"
        entity.verification_code_expires_at = datetime.now(timezone.utc)
        entity.verification_attempts = 2
        model = user_entity_to_model(entity)
        restored = user_model_to_entity(model)
        assert restored.verification_code_hash == "somehash"
        assert restored.verification_code_expires_at == entity.verification_code_expires_at
        assert restored.verification_attempts == 2


class TestCompanyGameMapper:
    def test_round_trip(self) -> None:
        entity = CompanyGame.create("CS2")
        model = company_game_entity_to_model(entity)
        restored = company_game_model_to_entity(model)
        assert restored.game == "CS2"


class TestSubscriptionPlanMapper:
    def test_round_trip(self) -> None:
        entity = SubscriptionPlan.create("monthly", uuid4(), duration_days=30)
        model = subscription_plan_entity_to_model(entity)
        restored = subscription_plan_model_to_entity(model)
        assert restored.type == "monthly"
        assert restored.duration_days == 30


class TestSubscriptionMapper:
    def test_round_trip(self) -> None:
        entity = Subscription.create(user_id=uuid4(), plan_id=uuid4())
        model = subscription_entity_to_model(entity)
        restored = subscription_model_to_entity(model)
        assert restored.user_id == entity.user_id


class TestPromocodeMapper:
    def test_round_trip(self) -> None:
        entity = PromocodeEntity.create("SAVE10", uuid4())
        model = promocode_entity_to_model(entity)
        restored = promocode_model_to_entity(model)
        assert restored.code == "SAVE10"


class TestPaymentMapper:
    def test_round_trip(self) -> None:
        now = datetime.utcnow()
        entity = Payment(
            id=uuid4(),
            user_id=uuid4(),
            plan_id=uuid4(),
            amount=Decimal("99.99"),
            status="pending",
            robokassa_invoice_id="inv-1",
            idempotency_key="key-1",
            paid_at=None,
            created_at=now,
            updated_at=now,
        )
        model = payment_entity_to_model(entity)
        restored = payment_model_to_entity(model)
        assert restored.amount == entity.amount
        assert restored.status == entity.status


class TestPaymentEventMapper:
    def test_round_trip(self) -> None:
        entity = PaymentEvent.create("payment.success", {"amount": 100})
        model = payment_event_entity_to_model(entity)
        restored = payment_event_model_to_entity(model)
        assert restored.event_type == "payment.success"
        assert restored.payload == {"amount": 100}

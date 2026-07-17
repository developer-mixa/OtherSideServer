"""Payment use case tests."""

from decimal import Decimal
from uuid import uuid4

import hashlib
import pytest

from application.dtos import PaymentInitDTO
from application.use_cases.payments import InitiatePaymentUseCase, ProcessRobokassaWebhookUseCase
from domain.entities import Payment, Subscription, SubscriptionPlan, User
from domain.exceptions import DuplicateEntityError, PaymentVerificationError
from infrastructure.payments.robokassa import RobokassaClient
from tests.conftest import FakeUnitOfWork


@pytest.fixture
def robokassa() -> RobokassaClient:
    return RobokassaClient(
        merchant_login="demo",
        password1="pass1",
        password2="pass2",
        is_test=True,
    )


@pytest.fixture
def remove_ad_plan(fake_uow: FakeUnitOfWork) -> SubscriptionPlan:
    plan = SubscriptionPlan.create("remove_ad", price_amount=Decimal("499.00"))
    fake_uow._store.subscription_plans[plan.id] = plan
    return plan


@pytest.fixture
def paying_user(fake_uow: FakeUnitOfWork) -> User:
    user = User.create("buyer", "buyer@example.com", "hash")
    fake_uow._store.users[user.id] = user
    return user


class TestInitiatePaymentUseCase:
    async def test_creates_pending_payment(
        self,
        fake_uow: FakeUnitOfWork,
        robokassa: RobokassaClient,
        paying_user: User,
        remove_ad_plan: SubscriptionPlan,
    ) -> None:
        use_case = InitiatePaymentUseCase(fake_uow, robokassa)
        result = await use_case.execute(
            paying_user.id,
            PaymentInitDTO(plan_id=remove_ad_plan.id, idempotency_key="key-1"),
        )
        assert result.status == "pending"
        assert result.amount == Decimal("499.00")
        assert "auth.robokassa.ru" in result.payment_url

    async def test_rejects_duplicate_permanent_subscription(
        self,
        fake_uow: FakeUnitOfWork,
        robokassa: RobokassaClient,
        paying_user: User,
        remove_ad_plan: SubscriptionPlan,
    ) -> None:
        sub = Subscription.create(
            user_id=paying_user.id,
            plan_id=remove_ad_plan.id,
            active_until=None,
        )
        fake_uow._store.subscriptions[sub.id] = sub
        use_case = InitiatePaymentUseCase(fake_uow, robokassa)
        with pytest.raises(DuplicateEntityError):
            await use_case.execute(
                paying_user.id,
                PaymentInitDTO(plan_id=remove_ad_plan.id, idempotency_key="key-2"),
            )


class TestProcessRobokassaWebhookUseCase:
    async def test_fulfills_payment_and_grants_subscription(
        self,
        fake_uow: FakeUnitOfWork,
        robokassa: RobokassaClient,
        paying_user: User,
        remove_ad_plan: SubscriptionPlan,
    ) -> None:
        payment = Payment.create(
            user_id=paying_user.id,
            plan_id=remove_ad_plan.id,
            amount=Decimal("499.00"),
            status="pending",
            robokassa_invoice_id="2001",
            idempotency_key="key-3",
        )
        fake_uow._store.payments[payment.id] = payment

        signature = hashlib.md5("499.00:2001:pass2".encode()).hexdigest()
        use_case = ProcessRobokassaWebhookUseCase(fake_uow, robokassa)
        response = await use_case.execute(
            {
                "OutSum": "499.00",
                "InvId": "2001",
                "SignatureValue": signature,
            }
        )
        assert response == "OK2001"
        updated = fake_uow._store.payments[payment.id]
        assert updated.status == "paid"
        subs = [
            s
            for s in fake_uow._store.subscriptions.values()
            if s.user_id == paying_user.id and s.plan_id == remove_ad_plan.id
        ]
        assert len(subs) == 1
        assert subs[0].active_until is None
        assert subs[0].source_payment_id == payment.id

    async def test_webhook_is_idempotent(
        self,
        fake_uow: FakeUnitOfWork,
        robokassa: RobokassaClient,
        paying_user: User,
        remove_ad_plan: SubscriptionPlan,
    ) -> None:
        payment = Payment.create(
            user_id=paying_user.id,
            plan_id=remove_ad_plan.id,
            amount=Decimal("499.00"),
            status="paid",
            robokassa_invoice_id="2002",
            idempotency_key="key-4",
        )
        fake_uow._store.payments[payment.id] = payment
        signature = hashlib.md5("499.00:2002:pass2".encode()).hexdigest()
        use_case = ProcessRobokassaWebhookUseCase(fake_uow, robokassa)
        response = await use_case.execute(
            {
                "OutSum": "499.00",
                "InvId": "2002",
                "SignatureValue": signature,
            }
        )
        assert response == "OK2002"
        assert len(fake_uow._store.subscriptions) == 0

    async def test_invalid_signature_raises(
        self,
        fake_uow: FakeUnitOfWork,
        robokassa: RobokassaClient,
    ) -> None:
        use_case = ProcessRobokassaWebhookUseCase(fake_uow, robokassa)
        with pytest.raises(PaymentVerificationError):
            await use_case.execute(
                {
                    "OutSum": "499.00",
                    "InvId": "3001",
                    "SignatureValue": "invalid",
                }
            )

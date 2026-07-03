"""Payment-related use cases."""

from __future__ import annotations

import logging
import secrets
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from application.dtos import PaymentDTO, PaymentInitDTO, PaymentInitResultDTO
from application.interfaces import UnitOfWorkProtocol
from application.mappers import payment_to_dto
from domain.entities import Payment, PaymentEvent, Subscription
from domain.exceptions import (
    AuthorizationError,
    DuplicateEntityError,
    EntityNotFoundError,
    PaymentVerificationError,
    ValidationError,
)
from infrastructure.payments.robokassa import RobokassaClient

logger = logging.getLogger(__name__)

_MAX_INVOICE_ATTEMPTS = 5


class InitiatePaymentUseCase:
    """Create a pending payment and return Robokassa redirect URL."""

    def __init__(self, uow: UnitOfWorkProtocol, robokassa: RobokassaClient) -> None:
        self._uow = uow
        self._robokassa = robokassa

    async def execute(self, user_id: UUID, dto: PaymentInitDTO) -> PaymentInitResultDTO:
        async with self._uow:
            existing = await self._uow.payments.get_by_idempotency_key(dto.idempotency_key)
            if existing:
                if existing.user_id != user_id:
                    raise AuthorizationError("Payment belongs to another user")
                return self._build_init_result(existing)

            plan = await self._uow.subscription_plans.get_by_id(dto.plan_id)
            if plan is None:
                raise EntityNotFoundError("SubscriptionPlan", dto.plan_id)
            if not plan.is_active:
                raise ValidationError("Subscription plan is not available for purchase")
            if not plan.is_remove_ad():
                raise ValidationError("Only remove_ad plans are supported for now")
            if plan.price_amount <= Decimal("0"):
                raise ValidationError("Plan price is not configured")

            permanent = await self._uow.subscriptions.get_permanent_by_user_and_plan(
                user_id, plan.id
            )
            if permanent is not None:
                raise DuplicateEntityError("Subscription", "plan_id", str(plan.id))

            invoice_id = await self._generate_unique_invoice_id()
            now = datetime.utcnow()
            payment = Payment.create(
                user_id=user_id,
                plan_id=plan.id,
                amount=plan.price_amount,
                status="pending",
                robokassa_invoice_id=invoice_id,
                idempotency_key=dto.idempotency_key,
                now=now,
            )
            await self._uow.payments.add(payment)
            await self._uow.payment_events.add(
                PaymentEvent.create(
                    event_type="payment.initiated",
                    payload={
                        "payment_id": str(payment.id),
                        "plan_id": str(plan.id),
                        "amount": str(plan.price_amount),
                    },
                    payment_id=payment.id,
                )
            )
            await self._uow.commit()

            payment_url = self._robokassa.build_payment_url(
                invoice_id=invoice_id,
                amount=plan.price_amount,
                description=f"Remove ads — {plan.type}",
            )
            return PaymentInitResultDTO(
                payment_id=payment.id,
                payment_url=payment_url,
                robokassa_invoice_id=invoice_id,
                amount=plan.price_amount,
                status=payment.status,
            )

    async def _generate_unique_invoice_id(self) -> str:
        for _ in range(_MAX_INVOICE_ATTEMPTS):
            candidate = str(secrets.randbelow(2_000_000_000) + 1)
            existing = await self._uow.payments.get_by_robokassa_invoice_id(candidate)
            if existing is None:
                return candidate
        raise ValidationError("Failed to generate unique Robokassa invoice id")

    def _build_init_result(self, payment: Payment) -> PaymentInitResultDTO:
        payment_url = self._robokassa.build_payment_url(
            invoice_id=payment.robokassa_invoice_id,
            amount=payment.amount,
            description="Remove ads",
        )
        return PaymentInitResultDTO(
            payment_id=payment.id,
            payment_url=payment_url,
            robokassa_invoice_id=payment.robokassa_invoice_id,
            amount=payment.amount,
            status=payment.status,
        )


class GetPaymentUseCase:
    """Return payment details for the authenticated owner."""

    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(self, user_id: UUID, payment_id: UUID) -> PaymentDTO:
        async with self._uow:
            payment = await self._uow.payments.get_by_id(payment_id)
            if payment is None:
                raise EntityNotFoundError("Payment", payment_id)
            if payment.user_id != user_id:
                raise AuthorizationError()
            return payment_to_dto(payment)


class ProcessRobokassaWebhookUseCase:
    """Verify Robokassa Result URL callback and fulfill paid remove_ad purchases."""

    def __init__(self, uow: UnitOfWorkProtocol, robokassa: RobokassaClient) -> None:
        self._uow = uow
        self._robokassa = robokassa

    async def execute(self, payload: dict[str, str]) -> str:
        invoice_id = payload.get("InvId", "")
        out_sum = payload.get("OutSum", "")
        signature = payload.get("SignatureValue", "")

        async with self._uow:
            event = PaymentEvent.create(
                event_type="robokassa.webhook",
                payload=dict(payload),
            )
            await self._uow.payment_events.add(event)

            if not invoice_id or not out_sum or not signature:
                await self._uow.commit()
                raise PaymentVerificationError("Missing required Robokassa fields")

            extra_params = {
                key: value
                for key, value in payload.items()
                if key.startswith("Shp_")
            }
            try:
                self._robokassa.verify_result_signature(
                    out_sum=out_sum,
                    invoice_id=invoice_id,
                    signature_value=signature,
                    extra_params=extra_params or None,
                )
            except PaymentVerificationError:
                await self._uow.commit()
                raise

            payment = await self._uow.payments.get_by_robokassa_invoice_id(invoice_id)
            if payment is None:
                event.payment_id = None
                await self._uow.commit()
                raise EntityNotFoundError("Payment", invoice_id)

            event.payment_id = payment.id

            if payment.status == "paid":
                await self._uow.payment_events.mark_processed(event.id)
                await self._uow.commit()
                return self._robokassa.format_result_response(invoice_id)

            if payment.status != "pending":
                await self._uow.commit()
                raise ValidationError(f"Payment cannot be fulfilled in status={payment.status}")

            if not RobokassaClient.amounts_equal(payment.amount, out_sum):
                await self._uow.commit()
                raise PaymentVerificationError("Payment amount mismatch")

            plan = await self._uow.subscription_plans.get_by_id(payment.plan_id)
            if plan is None:
                await self._uow.commit()
                raise EntityNotFoundError("SubscriptionPlan", payment.plan_id)

            now = datetime.utcnow()
            payment.mark_paid(now)
            await self._uow.payments.update(payment)

            existing = await self._uow.subscriptions.get_permanent_by_user_and_plan(
                payment.user_id, payment.plan_id
            )
            if existing is None:
                subscription = Subscription.create(
                    user_id=payment.user_id,
                    plan_id=payment.plan_id,
                    active_until=None,
                    source_payment_id=payment.id,
                )
                await self._uow.subscriptions.add(subscription)

            await self._uow.payment_events.add(
                PaymentEvent.create(
                    event_type="payment.fulfilled",
                    payload={
                        "payment_id": str(payment.id),
                        "invoice_id": invoice_id,
                    },
                    payment_id=payment.id,
                )
            )
            await self._uow.payment_events.mark_processed(event.id)
            await self._uow.commit()

            logger.info("Payment %s fulfilled via Robokassa invoice %s", payment.id, invoice_id)
            return self._robokassa.format_result_response(invoice_id)

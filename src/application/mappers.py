"""Domain ↔ DTO converters."""

from __future__ import annotations

from application.dtos import (
    CompanyGameDTO,
    PaymentDTO,
    PaymentEventDTO,
    PromocodeDTO,
    RoleDTO,
    SubscriptionDTO,
    SubscriptionPlanDTO,
    UserDTO,
)
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


def role_to_dto(entity: Role) -> RoleDTO:
    return RoleDTO(id=entity.id, role=entity.role)


def user_to_dto(entity: User) -> UserDTO:
    return UserDTO(
        id=entity.id,
        username=entity.username,
        email=entity.email,
        is_verified=entity.is_verified,
        role_id=entity.role_id,
    )


def company_game_to_dto(entity: CompanyGame) -> CompanyGameDTO:
    return CompanyGameDTO(id=entity.id, game=entity.game)


def subscription_plan_to_dto(entity: SubscriptionPlan) -> SubscriptionPlanDTO:
    return SubscriptionPlanDTO(id=entity.id, type=entity.type, game_id=entity.game_id)


def subscription_to_dto(entity: Subscription) -> SubscriptionDTO:
    return SubscriptionDTO(
        id=entity.id,
        user_id=entity.user_id,
        plan_id=entity.plan_id,
        active_until=entity.active_until,
    )


def promocode_to_dto(entity: PromocodeEntity) -> PromocodeDTO:
    return PromocodeDTO(
        id=entity.id,
        code=entity.code,
        plan_id=entity.plan_id,
        is_active=entity.is_active,
    )


def payment_to_dto(entity: Payment) -> PaymentDTO:
    return PaymentDTO(
        id=entity.id,
        user_id=entity.user_id,
        plan_id=entity.plan_id,
        amount=entity.amount,
        status=entity.status,
        robokassa_invoice_id=entity.robokassa_invoice_id,
        idempotency_key=entity.idempotency_key,
        paid_at=entity.paid_at,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def payment_event_to_dto(entity: PaymentEvent) -> PaymentEventDTO:
    return PaymentEventDTO(
        id=entity.id,
        payment_id=entity.payment_id,
        event_type=entity.event_type,
        payload=entity.payload,
        processed=entity.processed,
        created_at=entity.created_at,
    )

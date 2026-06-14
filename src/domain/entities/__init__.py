"""Domain entities — pure business objects without persistence concerns."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4


@dataclass
class Role:
    id: UUID
    role: str

    @classmethod
    def create(cls, role: str, entity_id: UUID | None = None) -> Role:
        return cls(id=entity_id or uuid4(), role=role)


@dataclass
class User:
    id: UUID
    username: str
    email: str
    password_hash: str
    is_verified: bool = False
    role_id: UUID | None = None

    @classmethod
    def create(
        cls,
        username: str,
        email: str,
        password_hash: str,
        role_id: UUID | None = None,
        entity_id: UUID | None = None,
    ) -> User:
        return cls(
            id=entity_id or uuid4(),
            username=username,
            email=email,
            password_hash=password_hash,
            role_id=role_id,
        )


@dataclass
class CompanyGame:
    id: UUID
    game: str

    @classmethod
    def create(cls, game: str, entity_id: UUID | None = None) -> CompanyGame:
        return cls(id=entity_id or uuid4(), game=game)


@dataclass
class SubscriptionPlan:
    id: UUID
    type: str
    game_id: UUID | None = None

    @classmethod
    def create(
        cls,
        plan_type: str,
        game_id: UUID | None = None,
        entity_id: UUID | None = None,
    ) -> SubscriptionPlan:
        return cls(id=entity_id or uuid4(), type=plan_type, game_id=game_id)


@dataclass
class Subscription:
    id: UUID
    user_id: UUID
    plan_id: UUID | None = None
    active_until: date | None = None

    @classmethod
    def create(
        cls,
        user_id: UUID,
        plan_id: UUID | None = None,
        active_until: date | None = None,
        entity_id: UUID | None = None,
    ) -> Subscription:
        return cls(
            id=entity_id or uuid4(),
            user_id=user_id,
            plan_id=plan_id,
            active_until=active_until,
        )

    def is_active(self, on_date: date | None = None) -> bool:
        check_date = on_date or date.today()
        return self.active_until is not None and self.active_until >= check_date


@dataclass
class PromocodeEntity:
    id: UUID
    code: str
    plan_id: UUID
    is_active: bool = True

    @classmethod
    def create(
        cls,
        code: str,
        plan_id: UUID,
        is_active: bool = True,
        entity_id: UUID | None = None,
    ) -> PromocodeEntity:
        return cls(
            id=entity_id or uuid4(),
            code=code.upper(),
            plan_id=plan_id,
            is_active=is_active,
        )


@dataclass
class Payment:
    id: UUID
    user_id: UUID
    plan_id: UUID
    amount: Decimal
    status: str
    robokassa_invoice_id: str
    idempotency_key: str
    created_at: datetime
    updated_at: datetime
    paid_at: datetime | None = None

    @classmethod
    def create(
        cls,
        user_id: UUID,
        plan_id: UUID,
        amount: Decimal,
        status: str,
        robokassa_invoice_id: str,
        idempotency_key: str,
        entity_id: UUID | None = None,
        now: datetime | None = None,
    ) -> Payment:
        timestamp = now or datetime.utcnow()
        return cls(
            id=entity_id or uuid4(),
            user_id=user_id,
            plan_id=plan_id,
            amount=amount,
            status=status,
            robokassa_invoice_id=robokassa_invoice_id,
            idempotency_key=idempotency_key,
            created_at=timestamp,
            updated_at=timestamp,
        )


@dataclass
class PaymentEvent:
    id: UUID
    payment_id: UUID | None
    event_type: str
    payload: dict[str, Any]
    processed: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create(
        cls,
        event_type: str,
        payload: dict[str, Any],
        payment_id: UUID | None = None,
        entity_id: UUID | None = None,
    ) -> PaymentEvent:
        return cls(
            id=entity_id or uuid4(),
            payment_id=payment_id,
            event_type=event_type,
            payload=payload,
        )

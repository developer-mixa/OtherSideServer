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
    price_amount: Decimal = Decimal("0.00")
    is_active: bool = True

    @classmethod
    def create(
        cls,
        plan_type: str,
        game_id: UUID | None = None,
        price_amount: Decimal = Decimal("0.00"),
        is_active: bool = True,
        entity_id: UUID | None = None,
    ) -> SubscriptionPlan:
        return cls(
            id=entity_id or uuid4(),
            type=plan_type,
            game_id=game_id,
            price_amount=price_amount,
            is_active=is_active,
        )

    def is_remove_ad(self) -> bool:
        return self.type.lower() == "remove_ad"


@dataclass
class Subscription:
    id: UUID
    user_id: UUID
    plan_id: UUID | None = None
    active_until: date | None = None
    source_payment_id: UUID | None = None

    @classmethod
    def create(
        cls,
        user_id: UUID,
        plan_id: UUID | None = None,
        active_until: date | None = None,
        source_payment_id: UUID | None = None,
        entity_id: UUID | None = None,
    ) -> Subscription:
        return cls(
            id=entity_id or uuid4(),
            user_id=user_id,
            plan_id=plan_id,
            active_until=active_until,
            source_payment_id=source_payment_id,
        )

    def is_permanent(self) -> bool:
        """Permanent (const) subscription — active_until is NULL."""
        return self.active_until is None

    def is_active(self, on_date: date | None = None) -> bool:
        check_date = on_date or date.today()
        if self.active_until is None:
            return True
        return self.active_until >= check_date


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

    def mark_paid(self, paid_at: datetime) -> None:
        """Transition payment to paid status."""
        self.status = "paid"
        self.paid_at = paid_at
        self.updated_at = paid_at

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
class SystemSettings:
    maintenance_mode: bool = False
    id: int = 1


@dataclass
class ContactSubmission:
    id: UUID
    name: str
    phone: str
    email: str
    message: str | None
    consent_personal_data: bool
    consent_privacy: bool
    created_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create(
        cls,
        name: str,
        phone: str,
        email: str,
        message: str | None,
        consent_personal_data: bool,
        consent_privacy: bool,
        entity_id: UUID | None = None,
    ) -> ContactSubmission:
        return cls(
            id=entity_id or uuid4(),
            name=name,
            phone=phone,
            email=email,
            message=message,
            consent_personal_data=consent_personal_data,
            consent_privacy=consent_privacy,
        )


@dataclass
class LandingSettings:
    countdown_title: str = "До релиза"
    release_date: date = field(default_factory=lambda: date(2026, 8, 1))
    id: int = 1


@dataclass
class RoadmapTask:
    id: UUID
    title: str
    description: str | None
    status: str
    sort_order: int

    @classmethod
    def create(
        cls,
        title: str,
        description: str | None = None,
        status: str = "pending",
        sort_order: int = 0,
        entity_id: UUID | None = None,
    ) -> RoadmapTask:
        return cls(
            id=entity_id or uuid4(),
            title=title,
            description=description,
            status=status,
            sort_order=sort_order,
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

"""Data Transfer Objects for application layer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID


@dataclass(slots=True)
class RoleDTO:
    id: UUID
    role: str


@dataclass(slots=True)
class UserDTO:
    id: UUID
    username: str
    email: str
    is_verified: bool
    role_id: UUID | None = None


@dataclass(slots=True)
class UserCreateDTO:
    username: str
    email: str
    password: str
    role_id: UUID | None = None


@dataclass(slots=True)
class AuthTokenDTO:
    access_token: str
    token_type: str = "bearer"


@dataclass(slots=True)
class CompanyGameDTO:
    id: UUID
    game: str


@dataclass(slots=True)
class CompanyGameCreateDTO:
    game: str


@dataclass(slots=True)
class SubscriptionPlanDTO:
    id: UUID
    type: str
    game_id: UUID | None = None


@dataclass(slots=True)
class SubscriptionPlanCreateDTO:
    type: str
    game_id: UUID | None = None


@dataclass(slots=True)
class SubscriptionDTO:
    id: UUID
    user_id: UUID
    plan_id: UUID | None
    active_until: date | None


@dataclass(slots=True)
class SubscriptionCreateDTO:
    user_id: UUID
    plan_id: UUID | None = None
    active_until: date | None = None


@dataclass(slots=True)
class PromocodeDTO:
    id: UUID
    code: str
    plan_id: UUID
    is_active: bool


@dataclass(slots=True)
class PromocodeCreateDTO:
    code: str
    plan_id: UUID
    is_active: bool = True


@dataclass(slots=True)
class PaymentDTO:
    id: UUID
    user_id: UUID
    plan_id: UUID
    amount: Decimal
    status: str
    robokassa_invoice_id: str
    idempotency_key: str
    paid_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class PaymentCreateDTO:
    user_id: UUID
    plan_id: UUID
    amount: Decimal
    status: str
    robokassa_invoice_id: str
    idempotency_key: str


@dataclass(slots=True)
class MaintenanceModeDTO:
    enabled: bool


@dataclass(slots=True)
class PaymentEventDTO:
    id: UUID
    payment_id: UUID | None
    event_type: str
    payload: dict[str, object]
    processed: bool
    created_at: datetime

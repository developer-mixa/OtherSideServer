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
    is_admin: bool = False
    is_blocked: bool = False


@dataclass(slots=True)
class UserCreateDTO:
    username: str
    email: str
    password: str


@dataclass(slots=True)
class UserUpdateDTO:
    username: str | None = None
    email: str | None = None
    role_id: UUID | None = None
    is_verified: bool | None = None
    is_blocked: bool | None = None


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
class CompanyGameUpdateDTO:
    game: str | None = None


@dataclass(slots=True)
class SubscriptionPlanDTO:
    id: UUID
    type: str
    game_id: UUID | None = None
    price_amount: Decimal = Decimal("0.00")
    is_active: bool = True


@dataclass(slots=True)
class SubscriptionPlanCreateDTO:
    type: str
    game_id: UUID | None = None
    price_amount: Decimal = Decimal("0.00")
    is_active: bool = True


@dataclass(slots=True)
class SubscriptionPlanUpdateDTO:
    type: str | None = None
    game_id: UUID | None = None
    price_amount: Decimal | None = None
    is_active: bool | None = None


@dataclass(slots=True)
class SubscriptionDTO:
    id: UUID
    user_id: UUID
    plan_id: UUID | None
    active_until: date | None
    source_payment_id: UUID | None = None


@dataclass(slots=True)
class SubscriptionCreateDTO:
    user_id: UUID
    plan_id: UUID | None = None
    active_until: date | None = None


@dataclass(slots=True)
class SubscriptionUpdateDTO:
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
class PromocodeUpdateDTO:
    code: str | None = None
    plan_id: UUID | None = None
    is_active: bool | None = None


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
class PaymentInitDTO:
    plan_id: UUID
    idempotency_key: str


@dataclass(slots=True)
class PaymentInitResultDTO:
    payment_id: UUID
    payment_url: str
    robokassa_invoice_id: str
    amount: Decimal
    status: str


@dataclass(slots=True)
class MaintenanceModeDTO:
    enabled: bool


@dataclass(slots=True)
class ContactSubmissionCreateDTO:
    name: str
    phone: str
    email: str
    message: str | None
    consent_personal_data: bool
    consent_privacy: bool


@dataclass(slots=True)
class ContactSubmissionDTO:
    id: UUID
    name: str
    phone: str
    email: str
    message: str | None
    consent_personal_data: bool
    consent_privacy: bool
    created_at: datetime


@dataclass(slots=True)
class LandingSettingsDTO:
    countdown_title: str
    release_date: date


@dataclass(slots=True)
class LandingSettingsUpdateDTO:
    countdown_title: str
    release_date: date


@dataclass(slots=True)
class RoadmapTaskDTO:
    id: UUID
    title: str
    description: str | None
    status: str
    sort_order: int


@dataclass(slots=True)
class RoadmapTaskCreateDTO:
    title: str
    description: str | None = None
    status: str = "pending"


@dataclass(slots=True)
class RoadmapTaskUpdateDTO:
    title: str | None = None
    description: str | None = None
    status: str | None = None
    sort_order: int | None = None


@dataclass(slots=True)
class LandingPublicDTO:
    countdown_title: str
    release_date: date
    tasks: list[RoadmapTaskDTO]


@dataclass(slots=True)
class PaymentEventDTO:
    id: UUID
    payment_id: UUID | None
    event_type: str
    payload: dict[str, object]
    processed: bool
    created_at: datetime

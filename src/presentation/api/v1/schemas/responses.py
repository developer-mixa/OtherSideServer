"""Pydantic v2 response schemas."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ErrorResponse(BaseModel):
    detail: str
    code: str | None = None


class RoleResponse(BaseModel):
    id: UUID
    role: str

    model_config = ConfigDict(from_attributes=True)


class UserResponse(BaseModel):
    id: UUID
    username: str
    email: str
    is_verified: bool
    role_id: UUID | None = None
    is_admin: bool = False
    is_blocked: bool = False

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    # Access token lifetime in seconds (RFC 6749 §5.1).
    expires_in: int


class CompanyGameResponse(BaseModel):
    id: UUID
    game: str

    model_config = ConfigDict(from_attributes=True)


class SubscriptionPlanResponse(BaseModel):
    id: UUID
    type: str
    game_id: UUID | None = None
    price_amount: Decimal = Decimal("0.00")
    is_active: bool = True
    duration_days: int | None = None

    model_config = ConfigDict(from_attributes=True, json_encoders={Decimal: str})


class SubscriptionResponse(BaseModel):
    id: UUID
    user_id: UUID
    plan_id: UUID | None
    active_until: date | None
    source_payment_id: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class PromocodeResponse(BaseModel):
    id: UUID
    code: str
    plan_id: UUID
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class PaymentResponse(BaseModel):
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

    model_config = ConfigDict(from_attributes=True, json_encoders={Decimal: str})


class PaymentInitResponse(BaseModel):
    payment_id: UUID
    payment_url: str
    robokassa_invoice_id: str
    amount: Decimal
    status: str

    model_config = ConfigDict(json_encoders={Decimal: str})


class MaintenanceModeResponse(BaseModel):
    enabled: bool


class ContactSubmissionResponse(BaseModel):
    id: UUID
    name: str
    phone: str
    email: str
    message: str | None
    consent_personal_data: bool
    consent_privacy: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RoadmapTaskResponse(BaseModel):
    id: UUID
    title: str
    description: str | None
    status: str
    sort_order: int

    model_config = ConfigDict(from_attributes=True)


class LandingSettingsResponse(BaseModel):
    countdown_title: str
    release_date: date

    model_config = ConfigDict(from_attributes=True)


class LandingPublicResponse(BaseModel):
    countdown_title: str
    release_date: date
    tasks: list[RoadmapTaskResponse]

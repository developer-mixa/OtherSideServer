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

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CompanyGameResponse(BaseModel):
    id: UUID
    game: str

    model_config = ConfigDict(from_attributes=True)


class SubscriptionPlanResponse(BaseModel):
    id: UUID
    type: str
    game_id: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class SubscriptionResponse(BaseModel):
    id: UUID
    user_id: UUID
    plan_id: UUID | None
    active_until: date | None

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

    model_config = ConfigDict(from_attributes=True)


class MaintenanceModeResponse(BaseModel):
    enabled: bool

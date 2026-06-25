"""Pydantic v2 request schemas."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    email: EmailStr
    password: str = Field(min_length=8)
    role_id: UUID | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RoleCreateRequest(BaseModel):
    role: str = Field(min_length=1, max_length=64)


class CompanyGameCreateRequest(BaseModel):
    game: str = Field(min_length=1, max_length=128)


class SubscriptionPlanCreateRequest(BaseModel):
    type: str = Field(min_length=1, max_length=64)
    game_id: UUID | None = None
    price_amount: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2)
    is_active: bool = True

    model_config = ConfigDict(json_encoders={Decimal: str})


class SubscriptionCreateRequest(BaseModel):
    user_id: UUID
    plan_id: UUID | None = None
    active_until: date | None = None


class PromocodeCreateRequest(BaseModel):
    code: str = Field(min_length=4, max_length=32)
    plan_id: UUID
    is_active: bool = True


class PaymentInitRequest(BaseModel):
    plan_id: UUID
    idempotency_key: str = Field(min_length=8, max_length=128)


class MaintenanceModeUpdateRequest(BaseModel):
    enabled: bool

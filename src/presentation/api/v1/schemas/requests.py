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
    consent_personal_data: bool


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RoleCreateRequest(BaseModel):
    role: str = Field(min_length=1, max_length=64)


class CompanyGameCreateRequest(BaseModel):
    game: str = Field(min_length=1, max_length=128)


class CompanyGameUpdateRequest(BaseModel):
    game: str | None = Field(default=None, min_length=1, max_length=128)


class SubscriptionPlanCreateRequest(BaseModel):
    type: str = Field(min_length=1, max_length=64)
    game_id: UUID | None = None
    price_amount: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2)
    is_active: bool = True
    duration_days: int | None = Field(default=None, ge=1)

    model_config = ConfigDict(json_encoders={Decimal: str})


class SubscriptionPlanUpdateRequest(BaseModel):
    type: str | None = Field(default=None, min_length=1, max_length=64)
    game_id: UUID | None = None
    price_amount: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    is_active: bool | None = None
    duration_days: int | None = Field(default=None, ge=1)

    model_config = ConfigDict(json_encoders={Decimal: str})


class SubscriptionCreateRequest(BaseModel):
    user_id: UUID
    plan_id: UUID | None = None
    active_until: date | None = None


class SubscriptionUpdateRequest(BaseModel):
    plan_id: UUID | None = None
    active_until: date | None = None


class PromocodeCreateRequest(BaseModel):
    code: str = Field(min_length=4, max_length=32)
    plan_id: UUID
    is_active: bool = True


class PromocodeUpdateRequest(BaseModel):
    code: str | None = Field(default=None, min_length=4, max_length=32)
    plan_id: UUID | None = None
    is_active: bool | None = None


class UserUpdateRequest(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=32)
    email: EmailStr | None = None
    role_id: UUID | None = None
    is_verified: bool | None = None
    is_blocked: bool | None = None


class PaymentInitRequest(BaseModel):
    plan_id: UUID
    idempotency_key: str = Field(min_length=8, max_length=128)


class MaintenanceModeUpdateRequest(BaseModel):
    enabled: bool


class ContactSubmitRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    phone: str = Field(min_length=5, max_length=32)
    email: EmailStr
    message: str | None = Field(default=None, max_length=2000)
    consent_personal_data: bool
    consent_privacy: bool


class LandingSettingsUpdateRequest(BaseModel):
    countdown_title: str = Field(min_length=1, max_length=128)
    release_date: date


class RoadmapTaskCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=500)
    status: str = Field(default="pending", pattern="^(pending|in_progress|completed)$")


class RoadmapTaskUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=500)
    status: str | None = Field(default=None, pattern="^(pending|in_progress|completed)$")
    sort_order: int | None = Field(default=None, ge=0)

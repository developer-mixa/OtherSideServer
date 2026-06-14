"""SQLAlchemy ORM persistence models."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.db.base import Base


class RoleModel(Base):
    __tablename__ = "roles"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    role: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    users: Mapped[list[UserModel]] = relationship(back_populates="role")


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    role_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("roles.id", ondelete="SET NULL")
    )

    role: Mapped[RoleModel | None] = relationship(back_populates="users")
    subscriptions: Mapped[list[SubscriptionModel]] = relationship(back_populates="user")
    payments: Mapped[list[PaymentModel]] = relationship(back_populates="user")


class CompanyGameModel(Base):
    __tablename__ = "company_games"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    game: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    plans: Mapped[list[SubscriptionPlanModel]] = relationship(back_populates="game")


class SubscriptionPlanModel(Base):
    __tablename__ = "subscription_plans"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    game_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("company_games.id", ondelete="SET NULL")
    )
    type: Mapped[str] = mapped_column(String, nullable=False)

    game: Mapped[CompanyGameModel | None] = relationship(back_populates="plans")
    subscriptions: Mapped[list[SubscriptionModel]] = relationship(back_populates="plan")
    promocodes: Mapped[list[PromocodeModel]] = relationship(back_populates="plan")
    payments: Mapped[list[PaymentModel]] = relationship(back_populates="plan")


class SubscriptionModel(Base):
    __tablename__ = "subscriptions"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    plan_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("subscription_plans.id", ondelete="SET NULL")
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    active_until: Mapped[date | None] = mapped_column(Date, nullable=True)

    plan: Mapped[SubscriptionPlanModel | None] = relationship(back_populates="subscriptions")
    user: Mapped[UserModel] = relationship(back_populates="subscriptions")


class PromocodeModel(Base):
    __tablename__ = "promocodes"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    plan_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("subscription_plans.id", ondelete="CASCADE"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    plan: Mapped[SubscriptionPlanModel] = relationship(back_populates="promocodes")


class PaymentModel(Base):
    __tablename__ = "payments"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    plan_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("subscription_plans.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    robokassa_invoice_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped[UserModel] = relationship(back_populates="payments")
    plan: Mapped[SubscriptionPlanModel] = relationship(back_populates="payments")
    events: Mapped[list[PaymentEventModel]] = relationship(back_populates="payment")


class PaymentEventModel(Base):
    __tablename__ = "payment_events"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    payment_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("payments.id", ondelete="CASCADE")
    )
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    payment: Mapped[PaymentModel | None] = relationship(back_populates="events")

"""SQLAlchemy ORM persistence models."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
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
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    role_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("roles.id", ondelete="SET NULL")
    )
    consent_personal_data: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    consent_personal_data_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    verification_code_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    verification_code_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    verification_code_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    verification_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

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
    price_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0.00")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)

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
    source_payment_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("payments.id", ondelete="SET NULL")
    )

    plan: Mapped[SubscriptionPlanModel | None] = relationship(back_populates="subscriptions")
    user: Mapped[UserModel] = relationship(back_populates="subscriptions")


class PromocodeModel(Base):
    __tablename__ = "promocodes"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    plan_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("subscription_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    plan: Mapped[SubscriptionPlanModel] = relationship(back_populates="promocodes")


class PaymentModel(Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'paid', 'failed', 'cancelled')",
            name="payments_status_check",
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    plan_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("subscription_plans.id", ondelete="CASCADE"),
        nullable=False,
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


class SystemSettingsModel(Base):
    __tablename__ = "system_settings"
    __table_args__ = (CheckConstraint("id = 1", name="system_settings_singleton"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    maintenance_mode: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class ContactSubmissionModel(Base):
    __tablename__ = "contact_submissions"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    consent_personal_data: Mapped[bool] = mapped_column(Boolean, nullable=False)
    consent_privacy: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)


class LandingSettingsModel(Base):
    __tablename__ = "landing_settings"
    __table_args__ = (CheckConstraint("id = 1", name="landing_settings_singleton"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    countdown_title: Mapped[str] = mapped_column(String, nullable=False, default="До релиза")
    release_date: Mapped[date] = mapped_column(Date, nullable=False)


class RoadmapTaskModel(Base):
    __tablename__ = "roadmap_tasks"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'in_progress', 'completed')",
            name="roadmap_tasks_status_check",
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


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


class RefreshTokenModel(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = (
        # Revocation sweeps (logout, password change, block) only ever touch live tokens.
        Index(
            "ix_refresh_tokens_user_id_active",
            "user_id",
            postgresql_where="revoked_at IS NULL",
        ),
        Index("ix_refresh_tokens_family_id", "family_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    family_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replaced_by_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("refresh_tokens.id", ondelete="SET NULL"),
        nullable=True,
    )

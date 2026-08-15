"""ORM model ↔ Domain entity mappers."""

from __future__ import annotations

from domain.entities import (
    CompanyGame,
    ContactSubmission,
    LandingSettings,
    Payment,
    PaymentEvent,
    PromocodeEntity,
    RoadmapTask,
    Role,
    Subscription,
    SubscriptionPlan,
    SystemSettings,
    User,
)
from infrastructure.db.models import (
    CompanyGameModel,
    ContactSubmissionModel,
    LandingSettingsModel,
    PaymentEventModel,
    PaymentModel,
    PromocodeModel,
    RoadmapTaskModel,
    RoleModel,
    SubscriptionModel,
    SubscriptionPlanModel,
    SystemSettingsModel,
    UserModel,
)


def role_model_to_entity(model: RoleModel) -> Role:
    return Role(id=model.id, role=model.role)


def role_entity_to_model(entity: Role) -> RoleModel:
    return RoleModel(id=entity.id, role=entity.role)


def user_model_to_entity(model: UserModel) -> User:
    return User(
        id=model.id,
        username=model.username,
        email=model.email,
        password_hash=model.password_hash,
        is_verified=model.is_verified,
        role_id=model.role_id,
        is_blocked=model.is_blocked,
        consent_personal_data=bool(model.consent_personal_data),
        consent_personal_data_at=model.consent_personal_data_at,
        verification_code_hash=model.verification_code_hash,
        verification_code_expires_at=model.verification_code_expires_at,
        verification_attempts=model.verification_attempts,
    )


def user_entity_to_model(entity: User) -> UserModel:
    return UserModel(
        id=entity.id,
        username=entity.username,
        email=entity.email,
        password_hash=entity.password_hash,
        is_verified=entity.is_verified,
        role_id=entity.role_id,
        is_blocked=entity.is_blocked,
        consent_personal_data=entity.consent_personal_data,
        consent_personal_data_at=entity.consent_personal_data_at,
        verification_code_hash=entity.verification_code_hash,
        verification_code_expires_at=entity.verification_code_expires_at,
        verification_attempts=entity.verification_attempts,
    )


def company_game_model_to_entity(model: CompanyGameModel) -> CompanyGame:
    return CompanyGame(id=model.id, game=model.game)


def company_game_entity_to_model(entity: CompanyGame) -> CompanyGameModel:
    return CompanyGameModel(id=entity.id, game=entity.game)


def subscription_plan_model_to_entity(model: SubscriptionPlanModel) -> SubscriptionPlan:
    return SubscriptionPlan(
        id=model.id,
        type=model.type,
        game_id=model.game_id,
        price_amount=model.price_amount,
        is_active=model.is_active,
        duration_days=model.duration_days,
    )


def subscription_plan_entity_to_model(entity: SubscriptionPlan) -> SubscriptionPlanModel:
    return SubscriptionPlanModel(
        id=entity.id,
        type=entity.type,
        game_id=entity.game_id,
        price_amount=entity.price_amount,
        is_active=entity.is_active,
        duration_days=entity.duration_days,
    )


def subscription_model_to_entity(model: SubscriptionModel) -> Subscription:
    return Subscription(
        id=model.id,
        user_id=model.user_id,
        plan_id=model.plan_id,
        active_until=model.active_until,
        source_payment_id=model.source_payment_id,
    )


def subscription_entity_to_model(entity: Subscription) -> SubscriptionModel:
    return SubscriptionModel(
        id=entity.id,
        user_id=entity.user_id,
        plan_id=entity.plan_id,
        active_until=entity.active_until,
        source_payment_id=entity.source_payment_id,
    )


def promocode_model_to_entity(model: PromocodeModel) -> PromocodeEntity:
    return PromocodeEntity(
        id=model.id,
        code=model.code,
        plan_id=model.plan_id,
        is_active=model.is_active,
    )


def promocode_entity_to_model(entity: PromocodeEntity) -> PromocodeModel:
    return PromocodeModel(
        id=entity.id,
        code=entity.code,
        plan_id=entity.plan_id,
        is_active=entity.is_active,
    )


def payment_model_to_entity(model: PaymentModel) -> Payment:
    return Payment(
        id=model.id,
        user_id=model.user_id,
        plan_id=model.plan_id,
        amount=model.amount,
        status=model.status,
        robokassa_invoice_id=model.robokassa_invoice_id,
        idempotency_key=model.idempotency_key,
        paid_at=model.paid_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def payment_entity_to_model(entity: Payment) -> PaymentModel:
    return PaymentModel(
        id=entity.id,
        user_id=entity.user_id,
        plan_id=entity.plan_id,
        amount=entity.amount,
        status=entity.status,
        robokassa_invoice_id=entity.robokassa_invoice_id,
        idempotency_key=entity.idempotency_key,
        paid_at=entity.paid_at,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def payment_event_model_to_entity(model: PaymentEventModel) -> PaymentEvent:
    return PaymentEvent(
        id=model.id,
        payment_id=model.payment_id,
        event_type=model.event_type,
        payload=model.payload,
        processed=model.processed,
        created_at=model.created_at,
    )


def payment_event_entity_to_model(entity: PaymentEvent) -> PaymentEventModel:
    return PaymentEventModel(
        id=entity.id,
        payment_id=entity.payment_id,
        event_type=entity.event_type,
        payload=entity.payload,
        processed=entity.processed,
        created_at=entity.created_at,
    )


def system_settings_model_to_entity(model: SystemSettingsModel) -> SystemSettings:
    return SystemSettings(id=model.id, maintenance_mode=model.maintenance_mode)


def system_settings_entity_to_model(entity: SystemSettings) -> SystemSettingsModel:
    return SystemSettingsModel(id=entity.id, maintenance_mode=entity.maintenance_mode)


def contact_submission_model_to_entity(model: ContactSubmissionModel) -> ContactSubmission:
    return ContactSubmission(
        id=model.id,
        name=model.name,
        phone=model.phone,
        email=model.email,
        message=model.message,
        consent_personal_data=model.consent_personal_data,
        consent_privacy=model.consent_privacy,
        created_at=model.created_at,
    )


def contact_submission_entity_to_model(entity: ContactSubmission) -> ContactSubmissionModel:
    return ContactSubmissionModel(
        id=entity.id,
        name=entity.name,
        phone=entity.phone,
        email=entity.email,
        message=entity.message,
        consent_personal_data=entity.consent_personal_data,
        consent_privacy=entity.consent_privacy,
        created_at=entity.created_at,
    )


def landing_settings_model_to_entity(model: LandingSettingsModel) -> LandingSettings:
    return LandingSettings(
        id=model.id,
        countdown_title=model.countdown_title,
        release_date=model.release_date,
    )


def landing_settings_entity_to_model(entity: LandingSettings) -> LandingSettingsModel:
    return LandingSettingsModel(
        id=entity.id,
        countdown_title=entity.countdown_title,
        release_date=entity.release_date,
    )


def roadmap_task_model_to_entity(model: RoadmapTaskModel) -> RoadmapTask:
    return RoadmapTask(
        id=model.id,
        title=model.title,
        description=model.description,
        status=model.status,
        sort_order=model.sort_order,
    )


def roadmap_task_entity_to_model(entity: RoadmapTask) -> RoadmapTaskModel:
    return RoadmapTaskModel(
        id=entity.id,
        title=entity.title,
        description=entity.description,
        status=entity.status,
        sort_order=entity.sort_order,
    )

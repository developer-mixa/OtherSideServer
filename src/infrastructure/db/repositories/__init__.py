"""SQLAlchemy repository implementations."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from application.unit_of_work import EntityState, IdentityMap
from domain.entities import (
    CompanyGame,
    Payment,
    PaymentEvent,
    PromocodeEntity,
    Role,
    Subscription,
    SubscriptionPlan,
    SystemSettings,
    User,
)
from infrastructure.db.models import (
    CompanyGameModel,
    PaymentEventModel,
    PaymentModel,
    PromocodeModel,
    RoleModel,
    SubscriptionModel,
    SubscriptionPlanModel,
    SystemSettingsModel,
    UserModel,
)
from infrastructure.mappers import (
    company_game_entity_to_model,
    company_game_model_to_entity,
    payment_entity_to_model,
    payment_event_entity_to_model,
    payment_event_model_to_entity,
    payment_model_to_entity,
    promocode_entity_to_model,
    promocode_model_to_entity,
    role_entity_to_model,
    role_model_to_entity,
    subscription_entity_to_model,
    subscription_model_to_entity,
    subscription_plan_entity_to_model,
    subscription_plan_model_to_entity,
    system_settings_entity_to_model,
    system_settings_model_to_entity,
    user_entity_to_model,
    user_model_to_entity,
)


class SqlAlchemyRoleRepository:
    def __init__(self, session: AsyncSession, identity_map: IdentityMap) -> None:
        self._session = session
        self._identity_map = identity_map

    async def get_by_id(self, role_id: UUID) -> Role | None:
        tracked = self._identity_map.get(Role, role_id)
        if tracked and tracked.state != EntityState.DELETED:
            return tracked.entity
        result = await self._session.execute(select(RoleModel).where(RoleModel.id == role_id))
        model = result.scalar_one_or_none()
        if model is None:
            return None
        entity = role_model_to_entity(model)
        self._identity_map.register(entity, EntityState.CLEAN)
        return entity

    async def get_by_name(self, name: str) -> Role | None:
        result = await self._session.execute(select(RoleModel).where(RoleModel.role == name))
        model = result.scalar_one_or_none()
        return role_model_to_entity(model) if model else None

    async def list_all(self) -> list[Role]:
        result = await self._session.execute(select(RoleModel))
        return [role_model_to_entity(m) for m in result.scalars().all()]

    async def add(self, entity: Role) -> Role:
        self._identity_map.register(entity, EntityState.NEW)
        self._session.add(role_entity_to_model(entity))
        return entity


class SqlAlchemyUserRepository:
    def __init__(self, session: AsyncSession, identity_map: IdentityMap) -> None:
        self._session = session
        self._identity_map = identity_map

    async def get_by_id(self, user_id: UUID) -> User | None:
        tracked = self._identity_map.get(User, user_id)
        if tracked and tracked.state != EntityState.DELETED:
            return tracked.entity
        result = await self._session.execute(select(UserModel).where(UserModel.id == user_id))
        model = result.scalar_one_or_none()
        if model is None:
            return None
        entity = user_model_to_entity(model)
        self._identity_map.register(entity, EntityState.CLEAN)
        return entity

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(UserModel).where(UserModel.email == email))
        model = result.scalar_one_or_none()
        return user_model_to_entity(model) if model else None

    async def get_by_username(self, username: str) -> User | None:
        result = await self._session.execute(
            select(UserModel).where(UserModel.username == username)
        )
        model = result.scalar_one_or_none()
        return user_model_to_entity(model) if model else None

    async def add(self, entity: User) -> User:
        self._identity_map.register(entity, EntityState.NEW)
        self._session.add(user_entity_to_model(entity))
        return entity

    async def list_all(self) -> list[User]:
        result = await self._session.execute(select(UserModel))
        return [user_model_to_entity(m) for m in result.scalars().all()]


class SqlAlchemyCompanyGameRepository:
    def __init__(self, session: AsyncSession, identity_map: IdentityMap) -> None:
        self._session = session
        self._identity_map = identity_map

    async def get_by_id(self, game_id: UUID) -> CompanyGame | None:
        result = await self._session.execute(
            select(CompanyGameModel).where(CompanyGameModel.id == game_id)
        )
        model = result.scalar_one_or_none()
        return company_game_model_to_entity(model) if model else None

    async def get_by_name(self, name: str) -> CompanyGame | None:
        result = await self._session.execute(
            select(CompanyGameModel).where(CompanyGameModel.game == name)
        )
        model = result.scalar_one_or_none()
        return company_game_model_to_entity(model) if model else None

    async def list_all(self) -> list[CompanyGame]:
        result = await self._session.execute(select(CompanyGameModel))
        return [company_game_model_to_entity(m) for m in result.scalars().all()]

    async def add(self, entity: CompanyGame) -> CompanyGame:
        self._identity_map.register(entity, EntityState.NEW)
        self._session.add(company_game_entity_to_model(entity))
        return entity

    async def delete(self, game_id: UUID) -> None:
        await self._session.execute(delete(CompanyGameModel).where(CompanyGameModel.id == game_id))


class SqlAlchemySubscriptionPlanRepository:
    def __init__(self, session: AsyncSession, identity_map: IdentityMap) -> None:
        self._session = session
        self._identity_map = identity_map

    async def get_by_id(self, plan_id: UUID) -> SubscriptionPlan | None:
        result = await self._session.execute(
            select(SubscriptionPlanModel).where(SubscriptionPlanModel.id == plan_id)
        )
        model = result.scalar_one_or_none()
        return subscription_plan_model_to_entity(model) if model else None

    async def list_all(self) -> list[SubscriptionPlan]:
        result = await self._session.execute(select(SubscriptionPlanModel))
        return [subscription_plan_model_to_entity(m) for m in result.scalars().all()]

    async def add(self, entity: SubscriptionPlan) -> SubscriptionPlan:
        self._identity_map.register(entity, EntityState.NEW)
        self._session.add(subscription_plan_entity_to_model(entity))
        return entity

    async def delete(self, plan_id: UUID) -> None:
        await self._session.execute(
            delete(SubscriptionPlanModel).where(SubscriptionPlanModel.id == plan_id)
        )


class SqlAlchemySubscriptionRepository:
    def __init__(self, session: AsyncSession, identity_map: IdentityMap) -> None:
        self._session = session
        self._identity_map = identity_map

    async def get_by_id(self, subscription_id: UUID) -> Subscription | None:
        result = await self._session.execute(
            select(SubscriptionModel).where(SubscriptionModel.id == subscription_id)
        )
        model = result.scalar_one_or_none()
        return subscription_model_to_entity(model) if model else None

    async def get_by_user(self, user_id: UUID) -> list[Subscription]:
        result = await self._session.execute(
            select(SubscriptionModel).where(SubscriptionModel.user_id == user_id)
        )
        return [subscription_model_to_entity(m) for m in result.scalars().all()]

    async def add(self, entity: Subscription) -> Subscription:
        self._identity_map.register(entity, EntityState.NEW)
        self._session.add(subscription_entity_to_model(entity))
        return entity

    async def delete(self, subscription_id: UUID) -> None:
        await self._session.execute(
            delete(SubscriptionModel).where(SubscriptionModel.id == subscription_id)
        )


class SqlAlchemyPromocodeRepository:
    def __init__(self, session: AsyncSession, identity_map: IdentityMap) -> None:
        self._session = session
        self._identity_map = identity_map

    async def get_by_id(self, promocode_id: UUID) -> PromocodeEntity | None:
        result = await self._session.execute(
            select(PromocodeModel).where(PromocodeModel.id == promocode_id)
        )
        model = result.scalar_one_or_none()
        return promocode_model_to_entity(model) if model else None

    async def get_by_code(self, code: str) -> PromocodeEntity | None:
        result = await self._session.execute(
            select(PromocodeModel).where(PromocodeModel.code == code.upper())
        )
        model = result.scalar_one_or_none()
        return promocode_model_to_entity(model) if model else None

    async def list_all(self) -> list[PromocodeEntity]:
        result = await self._session.execute(select(PromocodeModel))
        return [promocode_model_to_entity(m) for m in result.scalars().all()]

    async def add(self, entity: PromocodeEntity) -> PromocodeEntity:
        self._identity_map.register(entity, EntityState.NEW)
        self._session.add(promocode_entity_to_model(entity))
        return entity

    async def delete(self, promocode_id: UUID) -> None:
        await self._session.execute(
            delete(PromocodeModel).where(PromocodeModel.id == promocode_id)
        )


class SqlAlchemyPaymentRepository:
    def __init__(self, session: AsyncSession, identity_map: IdentityMap) -> None:
        self._session = session
        self._identity_map = identity_map

    async def get_by_id(self, payment_id: UUID) -> Payment | None:
        result = await self._session.execute(
            select(PaymentModel).where(PaymentModel.id == payment_id)
        )
        model = result.scalar_one_or_none()
        return payment_model_to_entity(model) if model else None

    async def get_by_idempotency_key(self, key: str) -> Payment | None:
        result = await self._session.execute(
            select(PaymentModel).where(PaymentModel.idempotency_key == key)
        )
        model = result.scalar_one_or_none()
        return payment_model_to_entity(model) if model else None

    async def list_by_user(self, user_id: UUID) -> list[Payment]:
        result = await self._session.execute(
            select(PaymentModel).where(PaymentModel.user_id == user_id)
        )
        return [payment_model_to_entity(m) for m in result.scalars().all()]

    async def add(self, entity: Payment) -> Payment:
        self._identity_map.register(entity, EntityState.NEW)
        self._session.add(payment_entity_to_model(entity))
        return entity


class SqlAlchemyPaymentEventRepository:
    def __init__(self, session: AsyncSession, identity_map: IdentityMap) -> None:
        self._session = session
        self._identity_map = identity_map

    async def add(self, entity: PaymentEvent) -> PaymentEvent:
        self._identity_map.register(entity, EntityState.NEW)
        self._session.add(payment_event_entity_to_model(entity))
        return entity

    async def list_unprocessed(self) -> list[PaymentEvent]:
        result = await self._session.execute(
            select(PaymentEventModel).where(PaymentEventModel.processed.is_(False))
        )
        return [payment_event_model_to_entity(m) for m in result.scalars().all()]


class SqlAlchemySystemSettingsRepository:
    """Singleton system settings row (id=1)."""

    _SINGLETON_ID = 1

    def __init__(self, session: AsyncSession, identity_map: IdentityMap) -> None:
        self._session = session
        self._identity_map = identity_map  # unused — singleton uses int PK

    async def get(self) -> SystemSettings:
        result = await self._session.execute(
            select(SystemSettingsModel).where(SystemSettingsModel.id == self._SINGLETON_ID)
        )
        model = result.scalar_one_or_none()
        if model is None:
            model = SystemSettingsModel(id=self._SINGLETON_ID, maintenance_mode=False)
            self._session.add(model)
            await self._session.flush()

        return system_settings_model_to_entity(model)

    async def set_maintenance_mode(self, enabled: bool) -> SystemSettings:
        settings = await self.get()
        settings.maintenance_mode = enabled
        await self._session.merge(system_settings_entity_to_model(settings))
        return settings

"""Application use cases (interactors)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from application.dtos import (
    AuthTokenDTO,
    CompanyGameCreateDTO,
    CompanyGameDTO,
    MaintenanceModeDTO,
    PaymentCreateDTO,
    PaymentDTO,
    PromocodeCreateDTO,
    PromocodeDTO,
    RoleDTO,
    SubscriptionCreateDTO,
    SubscriptionDTO,
    SubscriptionPlanCreateDTO,
    SubscriptionPlanDTO,
    UserCreateDTO,
    UserDTO,
)
from application.interfaces import UnitOfWorkProtocol
from application.mappers import (
    company_game_to_dto,
    payment_to_dto,
    promocode_to_dto,
    role_to_dto,
    subscription_plan_to_dto,
    subscription_to_dto,
    user_to_dto,
)
from application.use_cases.payments import (
    GetPaymentUseCase,
    InitiatePaymentUseCase,
    ProcessRobokassaWebhookUseCase,
)
from config.security import create_access_token, hash_password, verify_password
from config.settings import is_admin_role
from domain.entities import (
    CompanyGame,
    Payment,
    PromocodeEntity,
    Role,
    Subscription,
    SubscriptionPlan,
    User,
)
from domain.exceptions import (
    AuthenticationError,
    AuthorizationError,
    DuplicateEntityError,
    EntityNotFoundError,
)
from domain.value_objects import Email, Password, Username
from infrastructure.cache.maintenance_cache import MaintenanceModeCache


class RegisterUserUseCase:
    """Register a new user with hashed password."""

    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(self, dto: UserCreateDTO) -> UserDTO:
        username = Username(dto.username)
        email = Email(dto.email)
        Password(dto.password)

        async with self._uow:
            if await self._uow.users.get_by_email(email.value):
                raise DuplicateEntityError("User", "email", email.value)
            if await self._uow.users.get_by_username(username.value):
                raise DuplicateEntityError("User", "username", username.value)

            user = User.create(
                username=username.value,
                email=email.value,
                password_hash=hash_password(dto.password),
                role_id=dto.role_id,
            )
            await self._uow.users.add(user)
            await self._uow.commit()
            return user_to_dto(user)


class LoginUserUseCase:
    """Authenticate user and return JWT token."""

    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(self, email: str, password: str) -> AuthTokenDTO:
        normalized_email = Email(email).value

        async with self._uow:
            user = await self._uow.users.get_by_email(normalized_email)
            if user is None or not verify_password(password, user.password_hash):
                raise AuthenticationError()

            token = create_access_token({"sub": str(user.id)})
            return AuthTokenDTO(access_token=token)


class GetCurrentUserUseCase:
    """Get user by ID."""

    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(self, user_id: UUID) -> UserDTO:
        async with self._uow:
            user = await self._uow.users.get_by_id(user_id)
            if user is None:
                raise EntityNotFoundError("User", user_id)
            return user_to_dto(user)


class ListRolesUseCase:
    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(self) -> list[RoleDTO]:
        async with self._uow:
            roles = await self._uow.roles.list_all()
            return [role_to_dto(r) for r in roles]


class CreateRoleUseCase:
    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(self, role_name: str) -> RoleDTO:
        async with self._uow:
            existing = await self._uow.roles.get_by_name(role_name)
            if existing:
                raise DuplicateEntityError("Role", "role", role_name)
            role = Role.create(role_name)
            await self._uow.roles.add(role)
            await self._uow.commit()
            return role_to_dto(role)


class ListCompanyGamesUseCase:
    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(self) -> list[CompanyGameDTO]:
        async with self._uow:
            games = await self._uow.company_games.list_all()
            return [company_game_to_dto(g) for g in games]


class CreateCompanyGameUseCase:
    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(self, dto: CompanyGameCreateDTO) -> CompanyGameDTO:
        async with self._uow:
            existing = await self._uow.company_games.get_by_name(dto.game)
            if existing:
                raise DuplicateEntityError("CompanyGame", "game", dto.game)
            game = CompanyGame.create(dto.game)
            await self._uow.company_games.add(game)
            await self._uow.commit()
            return company_game_to_dto(game)


class DeleteCompanyGameUseCase:
    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(self, game_id: UUID) -> None:
        async with self._uow:
            game = await self._uow.company_games.get_by_id(game_id)
            if game is None:
                raise EntityNotFoundError("CompanyGame", game_id)
            await self._uow.company_games.delete(game_id)
            await self._uow.commit()


class ListSubscriptionPlansUseCase:
    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(self) -> list[SubscriptionPlanDTO]:
        async with self._uow:
            plans = await self._uow.subscription_plans.list_all()
            return [subscription_plan_to_dto(p) for p in plans]


class CreateSubscriptionPlanUseCase:
    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(self, dto: SubscriptionPlanCreateDTO) -> SubscriptionPlanDTO:
        async with self._uow:
            if dto.game_id:
                game = await self._uow.company_games.get_by_id(dto.game_id)
                if game is None:
                    raise EntityNotFoundError("CompanyGame", dto.game_id)
            plan = SubscriptionPlan.create(
                dto.type,
                dto.game_id,
                price_amount=dto.price_amount,
                is_active=dto.is_active,
            )
            await self._uow.subscription_plans.add(plan)
            await self._uow.commit()
            return subscription_plan_to_dto(plan)


class ListSubscriptionsUseCase:
    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(self, user_id: UUID | None = None) -> list[SubscriptionDTO]:
        async with self._uow:
            if user_id:
                subs = await self._uow.subscriptions.get_by_user(user_id)
            else:
                subs = []
                for user in await self._uow.users.list_all():
                    subs.extend(await self._uow.subscriptions.get_by_user(user.id))
            return [subscription_to_dto(s) for s in subs]


class CreateSubscriptionUseCase:
    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(self, dto: SubscriptionCreateDTO) -> SubscriptionDTO:
        async with self._uow:
            user = await self._uow.users.get_by_id(dto.user_id)
            if user is None:
                raise EntityNotFoundError("User", dto.user_id)
            if dto.plan_id:
                plan = await self._uow.subscription_plans.get_by_id(dto.plan_id)
                if plan is None:
                    raise EntityNotFoundError("SubscriptionPlan", dto.plan_id)
            sub = Subscription.create(
                user_id=dto.user_id,
                plan_id=dto.plan_id,
                active_until=dto.active_until,
            )
            await self._uow.subscriptions.add(sub)
            await self._uow.commit()
            return subscription_to_dto(sub)


class ListPromocodesUseCase:
    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(self) -> list[PromocodeDTO]:
        async with self._uow:
            codes = await self._uow.promocodes.list_all()
            return [promocode_to_dto(c) for c in codes]


class CreatePromocodeUseCase:
    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(self, dto: PromocodeCreateDTO) -> PromocodeDTO:
        async with self._uow:
            plan = await self._uow.subscription_plans.get_by_id(dto.plan_id)
            if plan is None:
                raise EntityNotFoundError("SubscriptionPlan", dto.plan_id)
            existing = await self._uow.promocodes.get_by_code(dto.code)
            if existing:
                raise DuplicateEntityError("Promocode", "code", dto.code)
            code = PromocodeEntity.create(dto.code, dto.plan_id, dto.is_active)
            await self._uow.promocodes.add(code)
            await self._uow.commit()
            return promocode_to_dto(code)


class ListPaymentsUseCase:
    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(self, user_id: UUID) -> list[PaymentDTO]:
        async with self._uow:
            payments = await self._uow.payments.list_by_user(user_id)
            return [payment_to_dto(p) for p in payments]


class CreatePaymentUseCase:
    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(self, dto: PaymentCreateDTO) -> PaymentDTO:
        async with self._uow:
            existing = await self._uow.payments.get_by_idempotency_key(dto.idempotency_key)
            if existing:
                return payment_to_dto(existing)

            user = await self._uow.users.get_by_id(dto.user_id)
            if user is None:
                raise EntityNotFoundError("User", dto.user_id)
            plan = await self._uow.subscription_plans.get_by_id(dto.plan_id)
            if plan is None:
                raise EntityNotFoundError("SubscriptionPlan", dto.plan_id)

            payment = Payment.create(
                user_id=dto.user_id,
                plan_id=dto.plan_id,
                amount=dto.amount,
                status=dto.status,
                robokassa_invoice_id=dto.robokassa_invoice_id,
                idempotency_key=dto.idempotency_key,
                now=datetime.utcnow(),
            )
            await self._uow.payments.add(payment)
            await self._uow.commit()
            return payment_to_dto(payment)


class GetMaintenanceModeUseCase:
    """Return current maintenance mode flag."""

    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(self) -> MaintenanceModeDTO:
        async with self._uow:
            settings = await self._uow.system_settings.get()
            MaintenanceModeCache.set(settings.maintenance_mode)
            return MaintenanceModeDTO(enabled=settings.maintenance_mode)


class SetMaintenanceModeUseCase:
    """Update maintenance mode (admin only)."""

    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(self, user_id: UUID, enabled: bool) -> MaintenanceModeDTO:
        async with self._uow:
            user = await self._uow.users.get_by_id(user_id)
            if user is None:
                raise EntityNotFoundError("User", user_id)
            if not is_admin_role(user.role_id):
                raise AuthorizationError()

            await self._uow.system_settings.set_maintenance_mode(enabled)
            await self._uow.commit()
            MaintenanceModeCache.set(enabled)
            return MaintenanceModeDTO(enabled=enabled)

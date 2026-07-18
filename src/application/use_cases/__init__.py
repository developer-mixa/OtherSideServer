"""Application use cases (interactors)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from application.auth import USER_ROLE_NAME, require_admin, user_is_admin
from application.dtos import (
    AuthTokenDTO,
    CompanyGameCreateDTO,
    CompanyGameDTO,
    CompanyGameUpdateDTO,
    MaintenanceModeDTO,
    PaymentCreateDTO,
    PaymentDTO,
    PromocodeCreateDTO,
    PromocodeDTO,
    PromocodeUpdateDTO,
    RoleDTO,
    SubscriptionCreateDTO,
    SubscriptionDTO,
    SubscriptionPlanCreateDTO,
    SubscriptionPlanDTO,
    SubscriptionPlanUpdateDTO,
    SubscriptionUpdateDTO,
    UserCreateDTO,
    UserDTO,
    UserUpdateDTO,
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
from application.users import build_user_dto
from config.security import create_access_token, hash_password, verify_password
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
    ValidationError,
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

            default_role = await self._uow.roles.get_by_name(USER_ROLE_NAME)
            if default_role is None:
                raise EntityNotFoundError("Role", USER_ROLE_NAME)

            user = User.create(
                username=username.value,
                email=email.value,
                password_hash=hash_password(dto.password),
                role_id=default_role.id,
            )
            await self._uow.users.add(user)
            await self._uow.commit()
            return await build_user_dto(self._uow, user)


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
            if user.is_blocked:
                raise AuthorizationError("User is blocked")

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
            return await build_user_dto(self._uow, user)


class ListUsersUseCase:
    """List all users (admin only)."""

    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(self, actor_id: UUID) -> list[UserDTO]:
        async with self._uow:
            await require_admin(self._uow, actor_id)
            users = await self._uow.users.list_all()
            return [await build_user_dto(self._uow, u) for u in users]


class UpdateUserUseCase:
    """Update a user's profile/role/status (admin only)."""

    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(self, actor_id: UUID, target_user_id: UUID, dto: UserUpdateDTO) -> UserDTO:
        async with self._uow:
            await require_admin(self._uow, actor_id)
            user = await self._uow.users.get_by_id(target_user_id)
            if user is None:
                raise EntityNotFoundError("User", target_user_id)

            if dto.username is not None:
                user.username = dto.username
            if dto.email is not None:
                user.email = dto.email
            if dto.role_id is not None:
                user.role_id = dto.role_id
            if dto.is_verified is not None:
                user.is_verified = dto.is_verified
            if dto.is_blocked is not None:
                user.is_blocked = dto.is_blocked

            await self._uow.users.update(user)
            await self._uow.commit()
            return await build_user_dto(self._uow, user)


class ListRolesUseCase:
    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(self, actor_id: UUID) -> list[RoleDTO]:
        async with self._uow:
            await require_admin(self._uow, actor_id)
            roles = await self._uow.roles.list_all()
            return [role_to_dto(r) for r in roles]


class CreateRoleUseCase:
    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(self, actor_id: UUID, role_name: str) -> RoleDTO:
        async with self._uow:
            await require_admin(self._uow, actor_id)
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

    async def execute(self, actor_id: UUID) -> list[CompanyGameDTO]:
        async with self._uow:
            await require_admin(self._uow, actor_id)
            games = await self._uow.company_games.list_all()
            return [company_game_to_dto(g) for g in games]


class CreateCompanyGameUseCase:
    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(self, actor_id: UUID, dto: CompanyGameCreateDTO) -> CompanyGameDTO:
        async with self._uow:
            await require_admin(self._uow, actor_id)
            existing = await self._uow.company_games.get_by_name(dto.game)
            if existing:
                raise DuplicateEntityError("CompanyGame", "game", dto.game)
            game = CompanyGame.create(dto.game)
            await self._uow.company_games.add(game)
            await self._uow.commit()
            return company_game_to_dto(game)


class UpdateCompanyGameUseCase:
    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(
        self, actor_id: UUID, game_id: UUID, dto: CompanyGameUpdateDTO
    ) -> CompanyGameDTO:
        async with self._uow:
            await require_admin(self._uow, actor_id)
            game = await self._uow.company_games.get_by_id(game_id)
            if game is None:
                raise EntityNotFoundError("CompanyGame", game_id)
            if dto.game is not None:
                existing = await self._uow.company_games.get_by_name(dto.game)
                if existing and existing.id != game_id:
                    raise DuplicateEntityError("CompanyGame", "game", dto.game)
                game.game = dto.game
            await self._uow.company_games.update(game)
            await self._uow.commit()
            return company_game_to_dto(game)


class DeleteCompanyGameUseCase:
    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(self, actor_id: UUID, game_id: UUID) -> None:
        async with self._uow:
            await require_admin(self._uow, actor_id)
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

    async def execute(self, actor_id: UUID, dto: SubscriptionPlanCreateDTO) -> SubscriptionPlanDTO:
        async with self._uow:
            await require_admin(self._uow, actor_id)
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


class UpdateSubscriptionPlanUseCase:
    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(
        self, actor_id: UUID, plan_id: UUID, dto: SubscriptionPlanUpdateDTO
    ) -> SubscriptionPlanDTO:
        async with self._uow:
            await require_admin(self._uow, actor_id)
            plan = await self._uow.subscription_plans.get_by_id(plan_id)
            if plan is None:
                raise EntityNotFoundError("SubscriptionPlan", plan_id)
            if dto.game_id is not None:
                game = await self._uow.company_games.get_by_id(dto.game_id)
                if game is None:
                    raise EntityNotFoundError("CompanyGame", dto.game_id)
                plan.game_id = dto.game_id
            if dto.type is not None:
                plan.type = dto.type
            if dto.price_amount is not None:
                plan.price_amount = dto.price_amount
            if dto.is_active is not None:
                plan.is_active = dto.is_active
            await self._uow.subscription_plans.update(plan)
            await self._uow.commit()
            return subscription_plan_to_dto(plan)


class DeleteSubscriptionPlanUseCase:
    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(self, actor_id: UUID, plan_id: UUID) -> None:
        async with self._uow:
            await require_admin(self._uow, actor_id)
            plan = await self._uow.subscription_plans.get_by_id(plan_id)
            if plan is None:
                raise EntityNotFoundError("SubscriptionPlan", plan_id)
            await self._uow.subscription_plans.delete(plan_id)
            await self._uow.commit()


class ListSubscriptionsUseCase:
    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(
        self,
        actor_id: UUID,
        user_id: UUID | None = None,
    ) -> list[SubscriptionDTO]:
        async with self._uow:
            actor = await self._uow.users.get_by_id(actor_id)
            if actor is None:
                raise EntityNotFoundError("User", actor_id)

            is_admin = await user_is_admin(self._uow, actor)
            if is_admin:
                if user_id:
                    subs = await self._uow.subscriptions.get_by_user(user_id)
                else:
                    subs = []
                    for user in await self._uow.users.list_all():
                        subs.extend(await self._uow.subscriptions.get_by_user(user.id))
            else:
                if user_id is not None and user_id != actor_id:
                    raise AuthorizationError()
                subs = await self._uow.subscriptions.get_by_user(actor_id)
            return [subscription_to_dto(s) for s in subs]


class CreateSubscriptionUseCase:
    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(self, actor_id: UUID, dto: SubscriptionCreateDTO) -> SubscriptionDTO:
        async with self._uow:
            await require_admin(self._uow, actor_id)
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


class UpdateSubscriptionUseCase:
    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(
        self, actor_id: UUID, subscription_id: UUID, dto: SubscriptionUpdateDTO
    ) -> SubscriptionDTO:
        async with self._uow:
            await require_admin(self._uow, actor_id)
            sub = await self._uow.subscriptions.get_by_id(subscription_id)
            if sub is None:
                raise EntityNotFoundError("Subscription", subscription_id)
            if dto.plan_id is not None:
                plan = await self._uow.subscription_plans.get_by_id(dto.plan_id)
                if plan is None:
                    raise EntityNotFoundError("SubscriptionPlan", dto.plan_id)
                sub.plan_id = dto.plan_id
            if dto.active_until is not None:
                sub.active_until = dto.active_until
            await self._uow.subscriptions.update(sub)
            await self._uow.commit()
            return subscription_to_dto(sub)


class DeleteSubscriptionUseCase:
    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(self, actor_id: UUID, subscription_id: UUID) -> None:
        async with self._uow:
            await require_admin(self._uow, actor_id)
            sub = await self._uow.subscriptions.get_by_id(subscription_id)
            if sub is None:
                raise EntityNotFoundError("Subscription", subscription_id)
            await self._uow.subscriptions.delete(subscription_id)
            await self._uow.commit()


class ListPromocodesUseCase:
    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(self, actor_id: UUID) -> list[PromocodeDTO]:
        async with self._uow:
            await require_admin(self._uow, actor_id)
            codes = await self._uow.promocodes.list_all()
            return [promocode_to_dto(c) for c in codes]


class CreatePromocodeUseCase:
    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(self, actor_id: UUID, dto: PromocodeCreateDTO) -> PromocodeDTO:
        async with self._uow:
            await require_admin(self._uow, actor_id)
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


class UpdatePromocodeUseCase:
    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(
        self, actor_id: UUID, promocode_id: UUID, dto: PromocodeUpdateDTO
    ) -> PromocodeDTO:
        async with self._uow:
            await require_admin(self._uow, actor_id)
            code = await self._uow.promocodes.get_by_id(promocode_id)
            if code is None:
                raise EntityNotFoundError("Promocode", promocode_id)
            if dto.plan_id is not None:
                plan = await self._uow.subscription_plans.get_by_id(dto.plan_id)
                if plan is None:
                    raise EntityNotFoundError("SubscriptionPlan", dto.plan_id)
                code.plan_id = dto.plan_id
            if dto.code is not None:
                new_code = dto.code.upper()
                existing = await self._uow.promocodes.get_by_code(new_code)
                if existing and existing.id != promocode_id:
                    raise DuplicateEntityError("Promocode", "code", new_code)
                code.code = new_code
            if dto.is_active is not None:
                code.is_active = dto.is_active
            await self._uow.promocodes.update(code)
            await self._uow.commit()
            return promocode_to_dto(code)


class DeletePromocodeUseCase:
    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(self, actor_id: UUID, promocode_id: UUID) -> None:
        async with self._uow:
            await require_admin(self._uow, actor_id)
            code = await self._uow.promocodes.get_by_id(promocode_id)
            if code is None:
                raise EntityNotFoundError("Promocode", promocode_id)
            await self._uow.promocodes.delete(promocode_id)
            await self._uow.commit()


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

            if dto.status != "pending":
                raise ValidationError("Only pending payments can be created")

            payment = Payment.create(
                user_id=dto.user_id,
                plan_id=dto.plan_id,
                amount=dto.amount,
                status="pending",
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
            await require_admin(self._uow, user_id)

            await self._uow.system_settings.set_maintenance_mode(enabled)
            await self._uow.commit()
            MaintenanceModeCache.set(enabled)
            return MaintenanceModeDTO(enabled=enabled)

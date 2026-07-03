"""Dishka DI providers."""

from collections.abc import AsyncIterator

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from application.use_cases import (
    CreateCompanyGameUseCase,
    CreatePaymentUseCase,
    CreatePromocodeUseCase,
    CreateRoleUseCase,
    CreateSubscriptionPlanUseCase,
    CreateSubscriptionUseCase,
    DeleteCompanyGameUseCase,
    GetCurrentUserUseCase,
    GetMaintenanceModeUseCase,
    GetPaymentUseCase,
    InitiatePaymentUseCase,
    ListCompanyGamesUseCase,
    ListPaymentsUseCase,
    ListPromocodesUseCase,
    ListRolesUseCase,
    ListSubscriptionPlansUseCase,
    ListSubscriptionsUseCase,
    LoginUserUseCase,
    ProcessRobokassaWebhookUseCase,
    RegisterUserUseCase,
    SetMaintenanceModeUseCase,
)
from application.use_cases.contact import ListContactSubmissionsUseCase, SubmitContactUseCase
from application.use_cases.landing import (
    CreateRoadmapTaskUseCase,
    DeleteRoadmapTaskUseCase,
    GetLandingPublicUseCase,
    GetLandingSettingsUseCase,
    ListRoadmapTasksUseCase,
    UpdateLandingSettingsUseCase,
    UpdateRoadmapTaskUseCase,
)
from config.settings import settings
from infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from infrastructure.payments.robokassa import RobokassaClient


class AppProvider(Provider):
    """Application-wide dependency injection container."""

    @provide(scope=Scope.APP)
    def engine(self) -> async_sessionmaker[AsyncSession]:
        engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
        return async_sessionmaker(engine, expire_on_commit=False)

    @provide(scope=Scope.REQUEST)
    async def session(
        self, factory: async_sessionmaker[AsyncSession]
    ) -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            yield session

    @provide(scope=Scope.REQUEST)
    def unit_of_work(self, session: AsyncSession) -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(session)

    @provide(scope=Scope.REQUEST)
    def register_user(self, uow: SqlAlchemyUnitOfWork) -> RegisterUserUseCase:
        return RegisterUserUseCase(uow)

    @provide(scope=Scope.REQUEST)
    def login_user(self, uow: SqlAlchemyUnitOfWork) -> LoginUserUseCase:
        return LoginUserUseCase(uow)

    @provide(scope=Scope.REQUEST)
    def get_current_user(self, uow: SqlAlchemyUnitOfWork) -> GetCurrentUserUseCase:
        return GetCurrentUserUseCase(uow)

    @provide(scope=Scope.REQUEST)
    def list_roles(self, uow: SqlAlchemyUnitOfWork) -> ListRolesUseCase:
        return ListRolesUseCase(uow)

    @provide(scope=Scope.REQUEST)
    def create_role(self, uow: SqlAlchemyUnitOfWork) -> CreateRoleUseCase:
        return CreateRoleUseCase(uow)

    @provide(scope=Scope.REQUEST)
    def list_company_games(self, uow: SqlAlchemyUnitOfWork) -> ListCompanyGamesUseCase:
        return ListCompanyGamesUseCase(uow)

    @provide(scope=Scope.REQUEST)
    def create_company_game(self, uow: SqlAlchemyUnitOfWork) -> CreateCompanyGameUseCase:
        return CreateCompanyGameUseCase(uow)

    @provide(scope=Scope.REQUEST)
    def delete_company_game(self, uow: SqlAlchemyUnitOfWork) -> DeleteCompanyGameUseCase:
        return DeleteCompanyGameUseCase(uow)

    @provide(scope=Scope.REQUEST)
    def list_subscription_plans(self, uow: SqlAlchemyUnitOfWork) -> ListSubscriptionPlansUseCase:
        return ListSubscriptionPlansUseCase(uow)

    @provide(scope=Scope.REQUEST)
    def create_subscription_plan(self, uow: SqlAlchemyUnitOfWork) -> CreateSubscriptionPlanUseCase:
        return CreateSubscriptionPlanUseCase(uow)

    @provide(scope=Scope.REQUEST)
    def list_subscriptions(self, uow: SqlAlchemyUnitOfWork) -> ListSubscriptionsUseCase:
        return ListSubscriptionsUseCase(uow)

    @provide(scope=Scope.REQUEST)
    def create_subscription(self, uow: SqlAlchemyUnitOfWork) -> CreateSubscriptionUseCase:
        return CreateSubscriptionUseCase(uow)

    @provide(scope=Scope.REQUEST)
    def list_promocodes(self, uow: SqlAlchemyUnitOfWork) -> ListPromocodesUseCase:
        return ListPromocodesUseCase(uow)

    @provide(scope=Scope.REQUEST)
    def create_promocode(self, uow: SqlAlchemyUnitOfWork) -> CreatePromocodeUseCase:
        return CreatePromocodeUseCase(uow)

    @provide(scope=Scope.REQUEST)
    def list_payments(self, uow: SqlAlchemyUnitOfWork) -> ListPaymentsUseCase:
        return ListPaymentsUseCase(uow)

    @provide(scope=Scope.REQUEST)
    def create_payment(self, uow: SqlAlchemyUnitOfWork) -> CreatePaymentUseCase:
        return CreatePaymentUseCase(uow)

    @provide(scope=Scope.APP)
    def robokassa_client(self) -> RobokassaClient:
        return RobokassaClient(
            merchant_login=settings.ROBOKASSA_MERCHANT_LOGIN,
            password1=settings.ROBOKASSA_PASSWORD1,
            password2=settings.ROBOKASSA_PASSWORD2,
            is_test=settings.ROBOKASSA_IS_TEST,
            payment_base_url=settings.ROBOKASSA_PAYMENT_URL,
        )

    @provide(scope=Scope.REQUEST)
    def initiate_payment(
        self, uow: SqlAlchemyUnitOfWork, robokassa: RobokassaClient
    ) -> InitiatePaymentUseCase:
        return InitiatePaymentUseCase(uow, robokassa)

    @provide(scope=Scope.REQUEST)
    def get_payment(self, uow: SqlAlchemyUnitOfWork) -> GetPaymentUseCase:
        return GetPaymentUseCase(uow)

    @provide(scope=Scope.REQUEST)
    def process_robokassa_webhook(
        self, uow: SqlAlchemyUnitOfWork, robokassa: RobokassaClient
    ) -> ProcessRobokassaWebhookUseCase:
        return ProcessRobokassaWebhookUseCase(uow, robokassa)

    @provide(scope=Scope.REQUEST)
    def get_maintenance_mode(self, uow: SqlAlchemyUnitOfWork) -> GetMaintenanceModeUseCase:
        return GetMaintenanceModeUseCase(uow)

    @provide(scope=Scope.REQUEST)
    def set_maintenance_mode(self, uow: SqlAlchemyUnitOfWork) -> SetMaintenanceModeUseCase:
        return SetMaintenanceModeUseCase(uow)

    @provide(scope=Scope.REQUEST)
    def submit_contact(self, uow: SqlAlchemyUnitOfWork) -> SubmitContactUseCase:
        return SubmitContactUseCase(uow)

    @provide(scope=Scope.REQUEST)
    def list_contact_submissions(self, uow: SqlAlchemyUnitOfWork) -> ListContactSubmissionsUseCase:
        return ListContactSubmissionsUseCase(uow)

    @provide(scope=Scope.REQUEST)
    def get_landing_public(self, uow: SqlAlchemyUnitOfWork) -> GetLandingPublicUseCase:
        return GetLandingPublicUseCase(uow)

    @provide(scope=Scope.REQUEST)
    def get_landing_settings(self, uow: SqlAlchemyUnitOfWork) -> GetLandingSettingsUseCase:
        return GetLandingSettingsUseCase(uow)

    @provide(scope=Scope.REQUEST)
    def update_landing_settings(self, uow: SqlAlchemyUnitOfWork) -> UpdateLandingSettingsUseCase:
        return UpdateLandingSettingsUseCase(uow)

    @provide(scope=Scope.REQUEST)
    def list_roadmap_tasks(self, uow: SqlAlchemyUnitOfWork) -> ListRoadmapTasksUseCase:
        return ListRoadmapTasksUseCase(uow)

    @provide(scope=Scope.REQUEST)
    def create_roadmap_task(self, uow: SqlAlchemyUnitOfWork) -> CreateRoadmapTaskUseCase:
        return CreateRoadmapTaskUseCase(uow)

    @provide(scope=Scope.REQUEST)
    def update_roadmap_task(self, uow: SqlAlchemyUnitOfWork) -> UpdateRoadmapTaskUseCase:
        return UpdateRoadmapTaskUseCase(uow)

    @provide(scope=Scope.REQUEST)
    def delete_roadmap_task(self, uow: SqlAlchemyUnitOfWork) -> DeleteRoadmapTaskUseCase:
        return DeleteRoadmapTaskUseCase(uow)

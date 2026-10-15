"""SQLAlchemy Unit of Work implementation."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from application.unit_of_work import IdentityMap
from infrastructure.db.repositories import (
    SqlAlchemyCompanyGameRepository,
    SqlAlchemyContactSubmissionRepository,
    SqlAlchemyLandingSettingsRepository,
    SqlAlchemyPaymentEventRepository,
    SqlAlchemyPaymentRepository,
    SqlAlchemyPromocodeRepository,
    SqlAlchemyRefreshTokenRepository,
    SqlAlchemyRoadmapTaskRepository,
    SqlAlchemyRoleRepository,
    SqlAlchemySubscriptionPlanRepository,
    SqlAlchemySubscriptionRepository,
    SqlAlchemySystemSettingsRepository,
    SqlAlchemyUserRepository,
)

logger = logging.getLogger(__name__)


class SqlAlchemyUnitOfWork:
    """Atomic transaction boundary with identity map."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._identity_map = IdentityMap()
        self.roles = SqlAlchemyRoleRepository(session, self._identity_map)
        self.users = SqlAlchemyUserRepository(session, self._identity_map)
        self.company_games = SqlAlchemyCompanyGameRepository(session, self._identity_map)
        self.subscription_plans = SqlAlchemySubscriptionPlanRepository(session, self._identity_map)
        self.subscriptions = SqlAlchemySubscriptionRepository(session, self._identity_map)
        self.promocodes = SqlAlchemyPromocodeRepository(session, self._identity_map)
        self.payments = SqlAlchemyPaymentRepository(session, self._identity_map)
        self.payment_events = SqlAlchemyPaymentEventRepository(session, self._identity_map)
        self.refresh_tokens = SqlAlchemyRefreshTokenRepository(session)
        self.system_settings = SqlAlchemySystemSettingsRepository(session, self._identity_map)
        self.contact_submissions = SqlAlchemyContactSubmissionRepository(
            session, self._identity_map
        )
        self.landing_settings = SqlAlchemyLandingSettingsRepository(session, self._identity_map)
        self.roadmap_tasks = SqlAlchemyRoadmapTaskRepository(session, self._identity_map)

    async def __aenter__(self) -> SqlAlchemyUnitOfWork:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        if exc_type is not None:
            await self.rollback()

    async def commit(self) -> None:
        try:
            await self._session.commit()
            self._identity_map.clear()
        except Exception:
            logger.exception("Failed to commit transaction")
            await self.rollback()
            raise

    async def rollback(self) -> None:
        await self._session.rollback()
        self._identity_map.clear()

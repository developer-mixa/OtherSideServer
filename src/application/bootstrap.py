"""One-time bootstrap of the initial admin user from environment variables."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import async_sessionmaker

from application.auth import ADMIN_ROLE_NAME
from config.security import hash_password
from config.settings import settings
from domain.entities import User
from domain.value_objects import Email, Password, Username
from infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork

logger = logging.getLogger(__name__)


async def bootstrap_admin_user(session_factory: async_sessionmaker) -> None:
    """Create the first admin account when bootstrap credentials are configured."""
    if not settings.bootstrap_admin_configured:
        return

    username = settings.BOOTSTRAP_ADMIN_USERNAME.strip()
    email = Email(settings.BOOTSTRAP_ADMIN_EMAIL).value
    Password(settings.BOOTSTRAP_ADMIN_PASSWORD)

    async with session_factory() as session:
        uow = SqlAlchemyUnitOfWork(session)
        async with uow:
            admin_role = await uow.roles.get_by_name(ADMIN_ROLE_NAME)
            if admin_role is None:
                logger.warning(
                    "Admin bootstrap skipped: role '%s' not found. Run database migrations first.",
                    ADMIN_ROLE_NAME,
                )
                return

            if await uow.users.exists_with_role_id(admin_role.id):
                logger.info("Admin bootstrap skipped: admin user already exists")
                return

            if await uow.users.get_by_email(email):
                logger.warning(
                    "Admin bootstrap skipped: email %s is already registered",
                    email,
                )
                return

            if await uow.users.get_by_username(username):
                logger.warning(
                    "Admin bootstrap skipped: username %s is already taken",
                    username,
                )
                return

            user = User.create(
                username=Username(username).value,
                email=email,
                password_hash=hash_password(settings.BOOTSTRAP_ADMIN_PASSWORD),
                role_id=admin_role.id,
                is_verified=True,
            )
            await uow.users.add(user)
            await uow.commit()
            logger.info("Initial admin user created for %s", email)

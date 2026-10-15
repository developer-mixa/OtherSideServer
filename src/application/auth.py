"""Authentication and authorization helpers."""

from __future__ import annotations

from uuid import UUID

from application.interfaces import UnitOfWorkProtocol
from domain.entities import User
from domain.exceptions import AuthorizationError, EntityNotFoundError

ADMIN_ROLE_NAME = "admin"
USER_ROLE_NAME = "user"


async def user_is_admin(uow: UnitOfWorkProtocol, user: User) -> bool:
    """Return True when the user is assigned the admin role in the database."""
    if user.role_id is None:
        return False
    role = await uow.roles.get_by_id(user.role_id)
    return role is not None and role.role == ADMIN_ROLE_NAME


async def require_admin(uow: UnitOfWorkProtocol, user_id: UUID) -> User:
    """Load user and verify admin role."""
    user = await uow.users.get_by_id(user_id)
    if user is None:
        raise EntityNotFoundError("User", user_id)
    # Re-check block status from the DB on every privileged action: a still-valid
    # token issued before the block must not keep working.
    if user.is_blocked:
        raise AuthorizationError("User is blocked", code="user_blocked")
    if not await user_is_admin(uow, user):
        raise AuthorizationError()
    return user

"""Build user DTOs with authorization metadata."""

from __future__ import annotations

from application.auth import user_is_admin
from application.dtos import UserDTO
from application.interfaces import UnitOfWorkProtocol
from application.mappers import user_to_dto
from domain.entities import User


async def build_user_dto(uow: UnitOfWorkProtocol, user: User) -> UserDTO:
    """Map a user entity to DTO including server-side admin flag."""
    base = user_to_dto(user)
    is_admin = await user_is_admin(uow, user)
    return UserDTO(
        id=base.id,
        username=base.username,
        email=base.email,
        is_verified=base.is_verified,
        role_id=base.role_id,
        is_admin=is_admin,
        is_blocked=base.is_blocked,
    )

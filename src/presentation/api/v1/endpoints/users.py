"""Users administration endpoints."""

from typing import Annotated
from uuid import UUID

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials

from application.dtos import UserUpdateDTO
from application.use_cases import ListUsersUseCase, UpdateUserUseCase
from config.deps import bearer_scheme, resolve_user_id
from presentation.api.v1.mappers import user_dto_to_response
from presentation.api.v1.schemas.requests import UserUpdateRequest
from presentation.api.v1.schemas.responses import UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserResponse])
@inject
async def list_users(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    use_case: FromDishka[ListUsersUseCase],
) -> list[UserResponse]:
    actor_id = resolve_user_id(credentials)
    users = await use_case.execute(actor_id)
    return [user_dto_to_response(u) for u in users]


@router.patch("/{user_id}", response_model=UserResponse)
@inject
async def update_user(
    user_id: UUID,
    body: UserUpdateRequest,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    use_case: FromDishka[UpdateUserUseCase],
) -> UserResponse:
    actor_id = resolve_user_id(credentials)
    dto = UserUpdateDTO(
        username=body.username,
        email=body.email,
        role_id=body.role_id,
        is_verified=body.is_verified,
        is_blocked=body.is_blocked,
    )
    result = await use_case.execute(actor_id, user_id, dto)
    return user_dto_to_response(result)

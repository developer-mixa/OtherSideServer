"""Roles endpoints."""

from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials

from application.use_cases import CreateRoleUseCase, ListRolesUseCase
from config.deps import bearer_scheme, resolve_user_id
from presentation.api.v1.mappers import role_dto_to_response
from presentation.api.v1.schemas.requests import RoleCreateRequest
from presentation.api.v1.schemas.responses import RoleResponse

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("", response_model=list[RoleResponse])
@inject
async def list_roles(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    use_case: FromDishka[ListRolesUseCase],
) -> list[RoleResponse]:
    actor_id = resolve_user_id(credentials)
    roles = await use_case.execute(actor_id)
    return [role_dto_to_response(r) for r in roles]


@router.post("", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
@inject
async def create_role(
    body: RoleCreateRequest,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    use_case: FromDishka[CreateRoleUseCase],
) -> RoleResponse:
    actor_id = resolve_user_id(credentials)
    result = await use_case.execute(actor_id, body.role)
    return role_dto_to_response(result)

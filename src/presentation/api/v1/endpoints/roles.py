"""Roles endpoints."""

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, status

from application.use_cases import CreateRoleUseCase, ListRolesUseCase
from presentation.api.v1.mappers import role_dto_to_response
from presentation.api.v1.schemas.requests import RoleCreateRequest
from presentation.api.v1.schemas.responses import RoleResponse

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("", response_model=list[RoleResponse])
@inject
async def list_roles(use_case: FromDishka[ListRolesUseCase]) -> list[RoleResponse]:
    roles = await use_case.execute()
    return [role_dto_to_response(r) for r in roles]


@router.post("", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
@inject
async def create_role(
    body: RoleCreateRequest,
    use_case: FromDishka[CreateRoleUseCase],
) -> RoleResponse:
    result = await use_case.execute(body.role)
    return role_dto_to_response(result)

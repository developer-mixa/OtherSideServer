"""Promocodes endpoints."""

from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials

from application.dtos import PromocodeCreateDTO
from application.use_cases import CreatePromocodeUseCase, ListPromocodesUseCase
from config.deps import bearer_scheme, resolve_user_id
from presentation.api.v1.mappers import promocode_dto_to_response
from presentation.api.v1.schemas.requests import PromocodeCreateRequest
from presentation.api.v1.schemas.responses import PromocodeResponse

router = APIRouter(prefix="/promocodes", tags=["promocodes"])


@router.get("", response_model=list[PromocodeResponse])
@inject
async def list_promocodes(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    use_case: FromDishka[ListPromocodesUseCase],
) -> list[PromocodeResponse]:
    actor_id = resolve_user_id(credentials)
    codes = await use_case.execute(actor_id)
    return [promocode_dto_to_response(c) for c in codes]


@router.post("", response_model=PromocodeResponse, status_code=status.HTTP_201_CREATED)
@inject
async def create_promocode(
    body: PromocodeCreateRequest,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    use_case: FromDishka[CreatePromocodeUseCase],
) -> PromocodeResponse:
    actor_id = resolve_user_id(credentials)
    dto = PromocodeCreateDTO(code=body.code, plan_id=body.plan_id, is_active=body.is_active)
    result = await use_case.execute(actor_id, dto)
    return promocode_dto_to_response(result)

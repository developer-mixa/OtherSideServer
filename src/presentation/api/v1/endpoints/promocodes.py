"""Promocodes endpoints."""

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, status

from application.dtos import PromocodeCreateDTO
from application.use_cases import CreatePromocodeUseCase, ListPromocodesUseCase
from presentation.api.v1.mappers import promocode_dto_to_response
from presentation.api.v1.schemas.requests import PromocodeCreateRequest
from presentation.api.v1.schemas.responses import PromocodeResponse

router = APIRouter(prefix="/promocodes", tags=["promocodes"])


@router.get("", response_model=list[PromocodeResponse])
@inject
async def list_promocodes(
    use_case: FromDishka[ListPromocodesUseCase],
) -> list[PromocodeResponse]:
    codes = await use_case.execute()
    return [promocode_dto_to_response(c) for c in codes]


@router.post("", response_model=PromocodeResponse, status_code=status.HTTP_201_CREATED)
@inject
async def create_promocode(
    body: PromocodeCreateRequest,
    use_case: FromDishka[CreatePromocodeUseCase],
) -> PromocodeResponse:
    dto = PromocodeCreateDTO(code=body.code, plan_id=body.plan_id, is_active=body.is_active)
    result = await use_case.execute(dto)
    return promocode_dto_to_response(result)

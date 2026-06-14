"""Company games CRUD endpoints."""

from uuid import UUID

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, status

from application.dtos import CompanyGameCreateDTO
from application.use_cases import (
    CreateCompanyGameUseCase,
    DeleteCompanyGameUseCase,
    ListCompanyGamesUseCase,
)
from presentation.api.v1.mappers import company_game_dto_to_response
from presentation.api.v1.schemas.requests import CompanyGameCreateRequest
from presentation.api.v1.schemas.responses import CompanyGameResponse

router = APIRouter(prefix="/games", tags=["games"])


@router.get("", response_model=list[CompanyGameResponse])
@inject
async def list_games(use_case: FromDishka[ListCompanyGamesUseCase]) -> list[CompanyGameResponse]:
    games = await use_case.execute()
    return [company_game_dto_to_response(g) for g in games]


@router.post("", response_model=CompanyGameResponse, status_code=status.HTTP_201_CREATED)
@inject
async def create_game(
    body: CompanyGameCreateRequest,
    use_case: FromDishka[CreateCompanyGameUseCase],
) -> CompanyGameResponse:
    dto = CompanyGameCreateDTO(game=body.game)
    result = await use_case.execute(dto)
    return company_game_dto_to_response(result)


@router.delete("/{game_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def delete_game(
    game_id: UUID,
    use_case: FromDishka[DeleteCompanyGameUseCase],
) -> None:
    await use_case.execute(game_id)

"""Company games CRUD endpoints."""

from typing import Annotated
from uuid import UUID

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials

from application.dtos import CompanyGameCreateDTO, CompanyGameUpdateDTO
from application.use_cases import (
    AuthenticateAccessTokenUseCase,
    CreateCompanyGameUseCase,
    DeleteCompanyGameUseCase,
    ListCompanyGamesUseCase,
    UpdateCompanyGameUseCase,
)
from config.deps import bearer_scheme, bearer_token
from presentation.api.v1.mappers import company_game_dto_to_response
from presentation.api.v1.schemas.requests import CompanyGameCreateRequest, CompanyGameUpdateRequest
from presentation.api.v1.schemas.responses import CompanyGameResponse

router = APIRouter(prefix="/games", tags=["games"])


@router.get("", response_model=list[CompanyGameResponse])
@inject
async def list_games(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    authenticate: FromDishka[AuthenticateAccessTokenUseCase],
    use_case: FromDishka[ListCompanyGamesUseCase],
) -> list[CompanyGameResponse]:
    actor_id = await authenticate.execute(bearer_token(credentials))
    games = await use_case.execute(actor_id)
    return [company_game_dto_to_response(g) for g in games]


@router.post("", response_model=CompanyGameResponse, status_code=status.HTTP_201_CREATED)
@inject
async def create_game(
    body: CompanyGameCreateRequest,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    authenticate: FromDishka[AuthenticateAccessTokenUseCase],
    use_case: FromDishka[CreateCompanyGameUseCase],
) -> CompanyGameResponse:
    actor_id = await authenticate.execute(bearer_token(credentials))
    dto = CompanyGameCreateDTO(game=body.game)
    result = await use_case.execute(actor_id, dto)
    return company_game_dto_to_response(result)


@router.patch("/{game_id}", response_model=CompanyGameResponse)
@inject
async def update_game(
    game_id: UUID,
    body: CompanyGameUpdateRequest,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    authenticate: FromDishka[AuthenticateAccessTokenUseCase],
    use_case: FromDishka[UpdateCompanyGameUseCase],
) -> CompanyGameResponse:
    actor_id = await authenticate.execute(bearer_token(credentials))
    dto = CompanyGameUpdateDTO(game=body.game)
    result = await use_case.execute(actor_id, game_id, dto)
    return company_game_dto_to_response(result)


@router.delete("/{game_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def delete_game(
    game_id: UUID,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    authenticate: FromDishka[AuthenticateAccessTokenUseCase],
    use_case: FromDishka[DeleteCompanyGameUseCase],
) -> None:
    actor_id = await authenticate.execute(bearer_token(credentials))
    await use_case.execute(actor_id, game_id)

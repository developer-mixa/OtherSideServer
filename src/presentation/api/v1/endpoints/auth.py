"""Authentication endpoints."""

from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials

from application.dtos import UserCreateDTO
from application.use_cases import GetCurrentUserUseCase, LoginUserUseCase, RegisterUserUseCase
from config.deps import bearer_scheme, resolve_user_id
from presentation.api.v1.mappers import token_dto_to_response, user_dto_to_response
from presentation.api.v1.schemas.requests import LoginRequest, RegisterRequest
from presentation.api.v1.schemas.responses import TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
@inject
async def register(
    body: RegisterRequest,
    use_case: FromDishka[RegisterUserUseCase],
) -> UserResponse:
    dto = UserCreateDTO(
        username=body.username,
        email=body.email,
        password=body.password,
        consent_personal_data=body.consent_personal_data,
    )
    result = await use_case.execute(dto)
    return user_dto_to_response(result)


@router.post("/login", response_model=TokenResponse)
@inject
async def login(
    body: LoginRequest,
    use_case: FromDishka[LoginUserUseCase],
) -> TokenResponse:
    result = await use_case.execute(body.email, body.password)
    return token_dto_to_response(result)


@router.get("/me", response_model=UserResponse)
@inject
async def me(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    use_case: FromDishka[GetCurrentUserUseCase],
) -> UserResponse:
    user_id = resolve_user_id(credentials)
    result = await use_case.execute(user_id)
    return user_dto_to_response(result)

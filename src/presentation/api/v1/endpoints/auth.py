"""Authentication endpoints."""

from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials

from application.dtos import UserCreateDTO
from application.use_cases import (
    AuthenticateAccessTokenUseCase,
    ChangePasswordUseCase,
    GetCurrentUserUseCase,
    LoginUserUseCase,
    LogoutUseCase,
    RefreshTokensUseCase,
    RegisterUserUseCase,
    ResendVerificationCodeUseCase,
    VerifyEmailUseCase,
)
from config.deps import bearer_scheme, bearer_token
from presentation.api.v1.mappers import token_dto_to_response, user_dto_to_response
from presentation.api.v1.schemas.requests import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    ResendVerificationRequest,
    VerifyEmailRequest,
)
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


@router.post("/verify-email", response_model=UserResponse)
@inject
async def verify_email(
    body: VerifyEmailRequest,
    use_case: FromDishka[VerifyEmailUseCase],
) -> UserResponse:
    result = await use_case.execute(body.email, body.code)
    return user_dto_to_response(result)


@router.post("/resend-verification", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def resend_verification(
    body: ResendVerificationRequest,
    use_case: FromDishka[ResendVerificationCodeUseCase],
) -> None:
    await use_case.execute(body.email)


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
    authenticate: FromDishka[AuthenticateAccessTokenUseCase],
    use_case: FromDishka[GetCurrentUserUseCase],
) -> UserResponse:
    user_id = await authenticate.execute(bearer_token(credentials))
    result = await use_case.execute(user_id)
    return user_dto_to_response(result)


@router.post("/refresh", response_model=TokenResponse)
@inject
async def refresh(
    body: RefreshTokenRequest,
    use_case: FromDishka[RefreshTokensUseCase],
) -> TokenResponse:
    result = await use_case.execute(body.refresh_token)
    return token_dto_to_response(result)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def logout(
    body: RefreshTokenRequest,
    use_case: FromDishka[LogoutUseCase],
) -> None:
    await use_case.execute(body.refresh_token)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def change_password(
    body: ChangePasswordRequest,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    authenticate: FromDishka[AuthenticateAccessTokenUseCase],
    use_case: FromDishka[ChangePasswordUseCase],
) -> None:
    user_id = await authenticate.execute(bearer_token(credentials))
    await use_case.execute(user_id, body.current_password, body.new_password)

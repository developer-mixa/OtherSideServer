"""DTO → Response schema mappers."""

from __future__ import annotations

from application.dtos import (
    AuthTokenDTO,
    CompanyGameDTO,
    PaymentDTO,
    PromocodeDTO,
    RoleDTO,
    SubscriptionDTO,
    SubscriptionPlanDTO,
    UserDTO,
)
from presentation.api.v1.schemas.responses import (
    CompanyGameResponse,
    PaymentResponse,
    PromocodeResponse,
    RoleResponse,
    SubscriptionPlanResponse,
    SubscriptionResponse,
    TokenResponse,
    UserResponse,
)


def user_dto_to_response(dto: UserDTO) -> UserResponse:
    return UserResponse.model_validate(dto)


def token_dto_to_response(dto: AuthTokenDTO) -> TokenResponse:
    return TokenResponse(access_token=dto.access_token, token_type=dto.token_type)


def role_dto_to_response(dto: RoleDTO) -> RoleResponse:
    return RoleResponse.model_validate(dto)


def company_game_dto_to_response(dto: CompanyGameDTO) -> CompanyGameResponse:
    return CompanyGameResponse.model_validate(dto)


def subscription_plan_dto_to_response(dto: SubscriptionPlanDTO) -> SubscriptionPlanResponse:
    return SubscriptionPlanResponse.model_validate(dto)


def subscription_dto_to_response(dto: SubscriptionDTO) -> SubscriptionResponse:
    return SubscriptionResponse.model_validate(dto)


def promocode_dto_to_response(dto: PromocodeDTO) -> PromocodeResponse:
    return PromocodeResponse.model_validate(dto)


def payment_dto_to_response(dto: PaymentDTO) -> PaymentResponse:
    return PaymentResponse.model_validate(dto)

"""DTO → Response schema mappers."""

from __future__ import annotations

from application.dtos import (
    AuthTokenDTO,
    CompanyGameDTO,
    ContactSubmissionDTO,
    LandingPublicDTO,
    LandingSettingsDTO,
    PaymentDTO,
    PromocodeDTO,
    RoadmapTaskDTO,
    RoleDTO,
    SubscriptionDTO,
    SubscriptionPlanDTO,
    UserDTO,
)
from presentation.api.v1.schemas.responses import (
    CompanyGameResponse,
    ContactSubmissionResponse,
    LandingPublicResponse,
    LandingSettingsResponse,
    PaymentResponse,
    PromocodeResponse,
    RoadmapTaskResponse,
    RoleResponse,
    SubscriptionPlanResponse,
    SubscriptionResponse,
    TokenResponse,
    UserResponse,
)


def user_dto_to_response(dto: UserDTO) -> UserResponse:
    return UserResponse.model_validate(dto)


def token_dto_to_response(dto: AuthTokenDTO) -> TokenResponse:
    return TokenResponse(
        access_token=dto.access_token,
        refresh_token=dto.refresh_token,
        token_type=dto.token_type,
        expires_in=dto.expires_in,
    )


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


def contact_submission_dto_to_response(dto: ContactSubmissionDTO) -> ContactSubmissionResponse:
    return ContactSubmissionResponse.model_validate(dto)


def landing_settings_dto_to_response(dto: LandingSettingsDTO) -> LandingSettingsResponse:
    return LandingSettingsResponse.model_validate(dto)


def roadmap_task_dto_to_response(dto: RoadmapTaskDTO) -> RoadmapTaskResponse:
    return RoadmapTaskResponse.model_validate(dto)


def landing_public_dto_to_response(dto: LandingPublicDTO) -> LandingPublicResponse:
    return LandingPublicResponse(
        countdown_title=dto.countdown_title,
        release_date=dto.release_date,
        tasks=[roadmap_task_dto_to_response(task) for task in dto.tasks],
    )

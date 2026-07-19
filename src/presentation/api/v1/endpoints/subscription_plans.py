"""Subscription plans endpoints."""

from typing import Annotated
from uuid import UUID

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials

from application.dtos import SubscriptionPlanCreateDTO, SubscriptionPlanUpdateDTO
from application.use_cases import (
    CreateSubscriptionPlanUseCase,
    DeleteSubscriptionPlanUseCase,
    ListSubscriptionPlansUseCase,
    UpdateSubscriptionPlanUseCase,
)
from config.deps import bearer_scheme, resolve_user_id
from presentation.api.v1.mappers import subscription_plan_dto_to_response
from presentation.api.v1.schemas.requests import (
    SubscriptionPlanCreateRequest,
    SubscriptionPlanUpdateRequest,
)
from presentation.api.v1.schemas.responses import SubscriptionPlanResponse

router = APIRouter(prefix="/plans", tags=["subscription-plans"])


@router.get("", response_model=list[SubscriptionPlanResponse])
@inject
async def list_plans(
    use_case: FromDishka[ListSubscriptionPlansUseCase],
) -> list[SubscriptionPlanResponse]:
    plans = await use_case.execute()
    return [subscription_plan_dto_to_response(p) for p in plans]


@router.post("", response_model=SubscriptionPlanResponse, status_code=status.HTTP_201_CREATED)
@inject
async def create_plan(
    body: SubscriptionPlanCreateRequest,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    use_case: FromDishka[CreateSubscriptionPlanUseCase],
) -> SubscriptionPlanResponse:
    actor_id = resolve_user_id(credentials)
    dto = SubscriptionPlanCreateDTO(
        type=body.type,
        game_id=body.game_id,
        price_amount=body.price_amount,
        is_active=body.is_active,
        duration_days=body.duration_days,
    )
    result = await use_case.execute(actor_id, dto)
    return subscription_plan_dto_to_response(result)


@router.patch("/{plan_id}", response_model=SubscriptionPlanResponse)
@inject
async def update_plan(
    plan_id: UUID,
    body: SubscriptionPlanUpdateRequest,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    use_case: FromDishka[UpdateSubscriptionPlanUseCase],
) -> SubscriptionPlanResponse:
    actor_id = resolve_user_id(credentials)
    dto = SubscriptionPlanUpdateDTO(
        type=body.type,
        game_id=body.game_id,
        price_amount=body.price_amount,
        is_active=body.is_active,
        duration_days=body.duration_days,
    )
    result = await use_case.execute(actor_id, plan_id, dto)
    return subscription_plan_dto_to_response(result)


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def delete_plan(
    plan_id: UUID,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    use_case: FromDishka[DeleteSubscriptionPlanUseCase],
) -> None:
    actor_id = resolve_user_id(credentials)
    await use_case.execute(actor_id, plan_id)

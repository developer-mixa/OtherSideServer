"""Subscription plans endpoints."""

from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials

from application.dtos import SubscriptionPlanCreateDTO
from application.use_cases import CreateSubscriptionPlanUseCase, ListSubscriptionPlansUseCase
from config.deps import bearer_scheme, resolve_user_id
from presentation.api.v1.mappers import subscription_plan_dto_to_response
from presentation.api.v1.schemas.requests import SubscriptionPlanCreateRequest
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
    )
    result = await use_case.execute(actor_id, dto)
    return subscription_plan_dto_to_response(result)

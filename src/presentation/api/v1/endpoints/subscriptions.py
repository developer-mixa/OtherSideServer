"""Subscriptions endpoints."""

from typing import Annotated
from uuid import UUID

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Depends, Query, status
from fastapi.security import HTTPAuthorizationCredentials

from application.dtos import SubscriptionCreateDTO
from application.use_cases import CreateSubscriptionUseCase, ListSubscriptionsUseCase
from config.deps import bearer_scheme, resolve_user_id
from presentation.api.v1.mappers import subscription_dto_to_response
from presentation.api.v1.schemas.requests import SubscriptionCreateRequest
from presentation.api.v1.schemas.responses import SubscriptionResponse

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.get("", response_model=list[SubscriptionResponse])
@inject
async def list_subscriptions(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    use_case: FromDishka[ListSubscriptionsUseCase],
    user_id: Annotated[UUID | None, Query()] = None,
) -> list[SubscriptionResponse]:
    actor_id = resolve_user_id(credentials)
    subs = await use_case.execute(actor_id, user_id)
    return [subscription_dto_to_response(s) for s in subs]


@router.post("", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
@inject
async def create_subscription(
    body: SubscriptionCreateRequest,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    use_case: FromDishka[CreateSubscriptionUseCase],
) -> SubscriptionResponse:
    actor_id = resolve_user_id(credentials)
    dto = SubscriptionCreateDTO(
        user_id=body.user_id,
        plan_id=body.plan_id,
        active_until=body.active_until,
    )
    result = await use_case.execute(actor_id, dto)
    return subscription_dto_to_response(result)

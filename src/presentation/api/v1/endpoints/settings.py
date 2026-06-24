"""System settings endpoints."""

from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials

from application.use_cases import GetMaintenanceModeUseCase, SetMaintenanceModeUseCase
from config.deps import bearer_scheme, resolve_user_id
from presentation.api.v1.schemas.requests import MaintenanceModeUpdateRequest
from presentation.api.v1.schemas.responses import MaintenanceModeResponse

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/maintenance", response_model=MaintenanceModeResponse)
@inject
async def get_maintenance_mode(
    use_case: FromDishka[GetMaintenanceModeUseCase],
) -> MaintenanceModeResponse:
    result = await use_case.execute()
    return MaintenanceModeResponse(enabled=result.enabled)


@router.patch("/maintenance", response_model=MaintenanceModeResponse)
@inject
async def update_maintenance_mode(
    body: MaintenanceModeUpdateRequest,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    use_case: FromDishka[SetMaintenanceModeUseCase],
) -> MaintenanceModeResponse:
    user_id = resolve_user_id(credentials)
    result = await use_case.execute(user_id, body.enabled)
    return MaintenanceModeResponse(enabled=result.enabled)

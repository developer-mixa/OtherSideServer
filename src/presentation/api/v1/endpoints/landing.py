"""Landing page public config and admin management."""

from typing import Annotated
from uuid import UUID

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials

from application.dtos import LandingSettingsUpdateDTO, RoadmapTaskCreateDTO, RoadmapTaskUpdateDTO
from application.use_cases.landing import (
    CreateRoadmapTaskUseCase,
    DeleteRoadmapTaskUseCase,
    GetLandingPublicUseCase,
    GetLandingSettingsUseCase,
    ListRoadmapTasksUseCase,
    UpdateLandingSettingsUseCase,
    UpdateRoadmapTaskUseCase,
)
from config.deps import bearer_scheme, resolve_user_id
from presentation.api.v1.mappers import (
    landing_public_dto_to_response,
    landing_settings_dto_to_response,
    roadmap_task_dto_to_response,
)
from presentation.api.v1.schemas.requests import (
    LandingSettingsUpdateRequest,
    RoadmapTaskCreateRequest,
    RoadmapTaskUpdateRequest,
)
from presentation.api.v1.schemas.responses import (
    LandingPublicResponse,
    LandingSettingsResponse,
    RoadmapTaskResponse,
)

router = APIRouter(prefix="/landing", tags=["landing"])


@router.get("/public", response_model=LandingPublicResponse)
@inject
async def get_landing_public(
    use_case: FromDishka[GetLandingPublicUseCase],
) -> LandingPublicResponse:
    result = await use_case.execute()
    return landing_public_dto_to_response(result)


@router.get("/settings", response_model=LandingSettingsResponse)
@inject
async def get_landing_settings(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    use_case: FromDishka[GetLandingSettingsUseCase],
) -> LandingSettingsResponse:
    user_id = resolve_user_id(credentials)
    result = await use_case.execute(user_id)
    return landing_settings_dto_to_response(result)


@router.patch("/settings", response_model=LandingSettingsResponse)
@inject
async def update_landing_settings(
    body: LandingSettingsUpdateRequest,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    use_case: FromDishka[UpdateLandingSettingsUseCase],
) -> LandingSettingsResponse:
    user_id = resolve_user_id(credentials)
    dto = LandingSettingsUpdateDTO(
        countdown_title=body.countdown_title,
        release_date=body.release_date,
    )
    result = await use_case.execute(user_id, dto)
    return landing_settings_dto_to_response(result)


@router.get("/tasks", response_model=list[RoadmapTaskResponse])
@inject
async def list_roadmap_tasks(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    use_case: FromDishka[ListRoadmapTasksUseCase],
) -> list[RoadmapTaskResponse]:
    user_id = resolve_user_id(credentials)
    results = await use_case.execute(user_id)
    return [roadmap_task_dto_to_response(item) for item in results]


@router.post("/tasks", response_model=RoadmapTaskResponse, status_code=status.HTTP_201_CREATED)
@inject
async def create_roadmap_task(
    body: RoadmapTaskCreateRequest,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    use_case: FromDishka[CreateRoadmapTaskUseCase],
) -> RoadmapTaskResponse:
    user_id = resolve_user_id(credentials)
    dto = RoadmapTaskCreateDTO(
        title=body.title,
        description=body.description,
        status=body.status,
    )
    result = await use_case.execute(user_id, dto)
    return roadmap_task_dto_to_response(result)


@router.patch("/tasks/{task_id}", response_model=RoadmapTaskResponse)
@inject
async def update_roadmap_task(
    task_id: UUID,
    body: RoadmapTaskUpdateRequest,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    use_case: FromDishka[UpdateRoadmapTaskUseCase],
) -> RoadmapTaskResponse:
    user_id = resolve_user_id(credentials)
    dto = RoadmapTaskUpdateDTO(
        title=body.title,
        description=body.description,
        status=body.status,
        sort_order=body.sort_order,
    )
    result = await use_case.execute(user_id, task_id, dto)
    return roadmap_task_dto_to_response(result)


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def delete_roadmap_task(
    task_id: UUID,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    use_case: FromDishka[DeleteRoadmapTaskUseCase],
) -> None:
    user_id = resolve_user_id(credentials)
    await use_case.execute(user_id, task_id)

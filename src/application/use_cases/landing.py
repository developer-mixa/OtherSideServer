"""Landing page countdown and roadmap use cases."""

from __future__ import annotations

from uuid import UUID

from application.auth import require_admin
from application.dtos import (
    LandingPublicDTO,
    LandingSettingsDTO,
    LandingSettingsUpdateDTO,
    RoadmapTaskCreateDTO,
    RoadmapTaskDTO,
    RoadmapTaskUpdateDTO,
)
from application.interfaces import UnitOfWorkProtocol
from application.mappers import landing_settings_to_dto, roadmap_task_to_dto
from domain.entities import RoadmapTask
from domain.exceptions import EntityNotFoundError, ValidationError

_VALID_STATUSES = frozenset({"pending", "in_progress", "completed"})


def _validate_status(status: str) -> None:
    if status not in _VALID_STATUSES:
        raise ValidationError(f"Invalid status: {status}", code="invalid_status")


class GetLandingPublicUseCase:
    """Return public landing countdown config and roadmap tasks."""

    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(self) -> LandingPublicDTO:
        async with self._uow:
            settings = await self._uow.landing_settings.get()
            tasks = await self._uow.roadmap_tasks.list_all()
            return LandingPublicDTO(
                countdown_title=settings.countdown_title,
                release_date=settings.release_date,
                tasks=[roadmap_task_to_dto(task) for task in tasks],
            )


class GetLandingSettingsUseCase:
    """Return landing settings for admin."""

    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(self, user_id: UUID) -> LandingSettingsDTO:
        async with self._uow:
            await require_admin(self._uow, user_id)
            settings = await self._uow.landing_settings.get()
            return landing_settings_to_dto(settings)


class UpdateLandingSettingsUseCase:
    """Update landing countdown settings (admin only)."""

    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(self, user_id: UUID, dto: LandingSettingsUpdateDTO) -> LandingSettingsDTO:
        async with self._uow:
            await require_admin(self._uow, user_id)
            settings = await self._uow.landing_settings.update(
                countdown_title=dto.countdown_title.strip(),
                release_date=dto.release_date,
            )
            await self._uow.commit()
            return landing_settings_to_dto(settings)


class ListRoadmapTasksUseCase:
    """List roadmap tasks (admin only)."""

    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(self, user_id: UUID) -> list[RoadmapTaskDTO]:
        async with self._uow:
            await require_admin(self._uow, user_id)
            tasks = await self._uow.roadmap_tasks.list_all()
            return [roadmap_task_to_dto(task) for task in tasks]


class CreateRoadmapTaskUseCase:
    """Create a roadmap task (admin only)."""

    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(self, user_id: UUID, dto: RoadmapTaskCreateDTO) -> RoadmapTaskDTO:
        _validate_status(dto.status)
        async with self._uow:
            await require_admin(self._uow, user_id)
            tasks = await self._uow.roadmap_tasks.list_all()
            next_order = max((task.sort_order for task in tasks), default=-1) + 1
            entity = RoadmapTask.create(
                title=dto.title.strip(),
                description=dto.description.strip() if dto.description else None,
                status=dto.status,
                sort_order=next_order,
            )
            await self._uow.roadmap_tasks.add(entity)
            await self._uow.commit()
            return roadmap_task_to_dto(entity)


class UpdateRoadmapTaskUseCase:
    """Update a roadmap task (admin only)."""

    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(
        self, user_id: UUID, task_id: UUID, dto: RoadmapTaskUpdateDTO
    ) -> RoadmapTaskDTO:
        if dto.status is not None:
            _validate_status(dto.status)

        async with self._uow:
            await require_admin(self._uow, user_id)
            task = await self._uow.roadmap_tasks.get_by_id(task_id)
            if task is None:
                raise EntityNotFoundError("RoadmapTask", task_id)

            if dto.title is not None:
                task.title = dto.title.strip()
            if dto.description is not None:
                task.description = dto.description.strip() or None
            if dto.status is not None:
                task.status = dto.status
            if dto.sort_order is not None:
                task.sort_order = dto.sort_order

            await self._uow.roadmap_tasks.update(task)
            await self._uow.commit()
            return roadmap_task_to_dto(task)


class DeleteRoadmapTaskUseCase:
    """Delete a roadmap task (admin only)."""

    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(self, user_id: UUID, task_id: UUID) -> None:
        async with self._uow:
            await require_admin(self._uow, user_id)
            task = await self._uow.roadmap_tasks.get_by_id(task_id)
            if task is None:
                raise EntityNotFoundError("RoadmapTask", task_id)
            await self._uow.roadmap_tasks.delete(task_id)
            await self._uow.commit()

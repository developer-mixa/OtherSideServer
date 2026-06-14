"""Unit of Work with identity map and dirty tracking."""

from __future__ import annotations

from enum import Enum
from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class EntityState(Enum):
    NEW = "new"
    CLEAN = "clean"
    DIRTY = "dirty"
    DELETED = "deleted"


class TrackedEntity(Generic[T]):
    """Wrapper for identity map dirty tracking."""

    def __init__(self, entity: T, state: EntityState = EntityState.NEW) -> None:
        self.entity = entity
        self.state = state
        self._original: dict[str, Any] | None = None

    def mark_dirty(self) -> None:
        if self.state == EntityState.CLEAN:
            self.state = EntityState.DIRTY

    def mark_deleted(self) -> None:
        self.state = EntityState.DELETED


class IdentityMap:
    """In-memory registry of tracked entities by type and id."""

    def __init__(self) -> None:
        self._store: dict[type[Any], dict[UUID, TrackedEntity[Any]]] = {}

    def register(self, entity: Any, state: EntityState = EntityState.NEW) -> TrackedEntity[Any]:
        entity_type = type(entity)
        entity_id: UUID = entity.id  # type: ignore[attr-defined]
        bucket = self._store.setdefault(entity_type, {})
        if entity_id in bucket:
            return bucket[entity_id]
        tracked = TrackedEntity(entity, state)
        bucket[entity_id] = tracked
        return tracked

    def get(self, entity_type: type[T], entity_id: UUID) -> TrackedEntity[T] | None:
        bucket = self._store.get(entity_type, {})
        tracked = bucket.get(entity_id)
        return tracked  # type: ignore[return-value]

    def iter_by_state(self, entity_type: type[T], state: EntityState) -> list[TrackedEntity[T]]:
        bucket = self._store.get(entity_type, {})
        return [t for t in bucket.values() if t.state == state]  # type: ignore[misc]

    def all_tracked(self) -> list[TrackedEntity[Any]]:
        result: list[TrackedEntity[Any]] = []
        for bucket in self._store.values():
            result.extend(bucket.values())
        return result

    def clear(self) -> None:
        self._store.clear()

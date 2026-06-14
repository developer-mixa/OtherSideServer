"""Unit of Work identity map tests."""

from uuid import uuid4

from application.unit_of_work import EntityState, IdentityMap, TrackedEntity
from domain.entities import Role


class TestIdentityMap:
    def test_register_new_entity(self) -> None:
        imap = IdentityMap()
        role = Role.create("admin")
        tracked = imap.register(role, EntityState.NEW)
        assert tracked.state == EntityState.NEW
        assert tracked.entity.role == "admin"

    def test_get_registered_entity(self) -> None:
        imap = IdentityMap()
        role = Role.create("admin")
        imap.register(role, EntityState.CLEAN)
        tracked = imap.get(Role, role.id)
        assert tracked is not None
        assert tracked.entity.id == role.id

    def test_iter_by_state(self) -> None:
        imap = IdentityMap()
        role1 = Role.create("admin")
        role2 = Role(id=uuid4(), role="user")
        imap.register(role1, EntityState.NEW)
        imap.register(role2, EntityState.CLEAN)
        new_entities = imap.iter_by_state(Role, EntityState.NEW)
        assert len(new_entities) == 1

    def test_tracked_entity_mark_dirty(self) -> None:
        role = Role.create("admin")
        tracked = TrackedEntity(role, EntityState.CLEAN)
        tracked.mark_dirty()
        assert tracked.state == EntityState.DIRTY

    def test_tracked_entity_mark_deleted(self) -> None:
        role = Role.create("admin")
        tracked = TrackedEntity(role)
        tracked.mark_deleted()
        assert tracked.state == EntityState.DELETED

    def test_clear(self) -> None:
        imap = IdentityMap()
        imap.register(Role.create("admin"))
        imap.clear()
        assert imap.all_tracked() == []

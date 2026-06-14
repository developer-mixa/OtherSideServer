"""Application mapper tests."""

from uuid import uuid4

from application.mappers import role_to_dto, user_to_dto
from domain.entities import Role, User


class TestApplicationMappers:
    def test_role_to_dto(self) -> None:
        role = Role(id=uuid4(), role="admin")
        dto = role_to_dto(role)
        assert dto.role == "admin"
        assert dto.id == role.id

    def test_user_to_dto(self) -> None:
        user = User.create("john", "john@example.com", "hash")
        dto = user_to_dto(user)
        assert dto.username == "john"
        assert dto.email == "john@example.com"

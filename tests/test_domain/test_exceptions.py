"""Domain exception tests."""

from uuid import uuid4

from domain.exceptions import (
    AuthenticationError,
    DomainError,
    DuplicateEntityError,
    EntityNotFoundError,
    ValidationError,
)


class TestDomainExceptions:
    def test_entity_not_found(self) -> None:
        uid = uuid4()
        exc = EntityNotFoundError("User", uid)
        assert "User" in exc.message
        assert exc.entity_id == uid

    def test_duplicate_entity(self) -> None:
        exc = DuplicateEntityError("User", "email", "a@b.com")
        assert exc.field == "email"

    def test_authentication_error_default(self) -> None:
        assert AuthenticationError().message == "Invalid credentials"

    def test_validation_error(self) -> None:
        exc = ValidationError("bad input")
        assert isinstance(exc, DomainError)

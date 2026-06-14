"""Presentation layer mapper tests."""

from uuid import uuid4

from application.dtos import UserDTO
from presentation.api.v1.mappers import user_dto_to_response


class TestPresentationMappers:
    def test_user_dto_to_response(self) -> None:
        dto = UserDTO(
            id=uuid4(),
            username="john",
            email="john@example.com",
            is_verified=True,
        )
        response = user_dto_to_response(dto)
        assert response.username == "john"
        assert response.is_verified is True

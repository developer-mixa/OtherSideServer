"""Security utility tests."""

from uuid import uuid4

import pytest

from config.security import (
    create_access_token,
    decode_access_token,
    get_user_id_from_token,
    hash_password,
    verify_password,
)
from domain.exceptions import AuthenticationError


class TestPasswordHashing:
    def test_hash_and_verify(self) -> None:
        hashed = hash_password("password123")
        assert verify_password("password123", hashed) is True
        assert verify_password("wrong", hashed) is False


class TestJWT:
    def test_create_and_decode_token(self) -> None:
        user_id = uuid4()
        token = create_access_token({"sub": str(user_id)})
        payload = decode_access_token(token)
        assert payload["sub"] == str(user_id)

    def test_get_user_id_from_token(self) -> None:
        user_id = uuid4()
        token = create_access_token({"sub": str(user_id)})
        assert get_user_id_from_token(token) == user_id

    def test_invalid_token_raises(self) -> None:
        with pytest.raises(AuthenticationError):
            decode_access_token("invalid.token.here")

    def test_token_missing_sub_raises(self) -> None:
        token = create_access_token({})
        with pytest.raises(AuthenticationError):
            get_user_id_from_token(token)

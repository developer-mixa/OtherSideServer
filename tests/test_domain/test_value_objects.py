"""Domain value object tests."""

import pytest

from domain.exceptions import ValidationError
from domain.value_objects import Email, Password, Promocode, Username


class TestEmail:
    def test_valid_email(self) -> None:
        email = Email("User@Example.COM")
        assert email.value == "user@example.com"

    def test_invalid_email_raises(self) -> None:
        with pytest.raises(ValidationError):
            Email("not-an-email")


class TestUsername:
    def test_valid_username(self) -> None:
        assert Username("user123").value == "user123"

    def test_too_short_raises(self) -> None:
        with pytest.raises(ValidationError):
            Username("ab")

    def test_non_alphanumeric_raises(self) -> None:
        with pytest.raises(ValidationError):
            Username("user_name")


class TestPassword:
    def test_valid_password(self) -> None:
        assert Password("password123").value == "password123"

    def test_too_short_raises(self) -> None:
        with pytest.raises(ValidationError):
            Password("short")


class TestPromocode:
    def test_normalizes_to_upper(self) -> None:
        assert Promocode("save10").value == "SAVE10"

    def test_too_short_raises(self) -> None:
        with pytest.raises(ValidationError):
            Promocode("abc")

"""Immutable value objects with validation."""

from __future__ import annotations

import re
from dataclasses import dataclass

from domain.exceptions import ValidationError

_EMAIL_RE = re.compile(r"^[^@]+@[^@]+\.[^@]+$")


@dataclass(frozen=True, slots=True)
class Email:
    """Validated email address."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()
        if not _EMAIL_RE.match(normalized):
            raise ValidationError(f"Invalid email: {self.value!r}")
        object.__setattr__(self, "value", normalized)


@dataclass(frozen=True, slots=True)
class Username:
    """Validated username (3-32 alphanumeric chars)."""

    value: str

    def __post_init__(self) -> None:
        if not 3 <= len(self.value) <= 32:
            raise ValidationError("Username must be 3-32 characters")
        if not self.value.isalnum():
            raise ValidationError("Username must be alphanumeric")


@dataclass(frozen=True, slots=True)
class Password:
    """Validated password (min 8 chars)."""

    value: str

    def __post_init__(self) -> None:
        if len(self.value) < 8:
            raise ValidationError("Password must be at least 8 characters")


@dataclass(frozen=True, slots=True)
class Promocode:
    """Validated promocode string."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().upper()
        if not 4 <= len(normalized) <= 32:
            raise ValidationError("Promocode must be 4-32 characters")
        object.__setattr__(self, "value", normalized)

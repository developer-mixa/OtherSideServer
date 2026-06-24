"""In-memory cache for maintenance mode flag."""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class _CacheEntry:
    value: bool
    expires_at: float


class MaintenanceModeCache:
    """Short-lived cache to reduce DB reads in middleware."""

    TTL_SECONDS = 5.0
    _entry: _CacheEntry | None = None

    @classmethod
    def get(cls) -> bool | None:
        """Return cached value if present and not expired."""
        if cls._entry is not None and time.monotonic() < cls._entry.expires_at:
            return cls._entry.value
        return None

    @classmethod
    def set(cls, value: bool) -> None:
        """Store value with TTL."""
        cls._entry = _CacheEntry(value=value, expires_at=time.monotonic() + cls.TTL_SECONDS)

    @classmethod
    def invalidate(cls) -> None:
        """Clear cached value."""
        cls._entry = None

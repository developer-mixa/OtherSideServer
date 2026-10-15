"""JWT, refresh token, and email verification code utilities.

Password hashing lives in ``infrastructure.security.passwords`` behind
``application.interfaces.PasswordHasherProtocol``.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import jwt

from config.settings import settings
from domain.exceptions import AuthenticationError

# 32 bytes from the OS CSPRNG: 256 bits, so the stored SHA-256 needs no salt or slow hash —
# brute-forcing it is infeasible, unlike a human-chosen password.
_REFRESH_TOKEN_BYTES = 32


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT access token."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": now})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALG)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT access token."""
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALG],
            # A token without an expiry would be valid forever; reject it outright
            # rather than relying on every issuer remembering to set one.
            options={"require": ["exp", "sub"]},
        )
        return payload
    except jwt.InvalidTokenError as exc:
        raise AuthenticationError("Invalid or expired token", code="token_invalid") from exc


def get_user_id_from_token(token: str) -> UUID:
    """Extract user ID from JWT token."""
    return user_id_from_claims(decode_access_token(token))


def user_id_from_claims(payload: dict[str, Any]) -> UUID:
    """Extract user ID from already verified JWT claims."""
    sub = payload.get("sub")
    if sub is None:
        raise AuthenticationError("Token missing subject", code="token_invalid")
    try:
        return UUID(sub)
    except (ValueError, TypeError) as exc:
        # A structurally valid token whose `sub` is not a UUID must be rejected as
        # unauthenticated, not bubble up as an unhandled 500.
        raise AuthenticationError("Token missing subject", code="token_invalid") from exc


def generate_verification_code() -> str:
    """Generate a random 6-digit email verification code."""
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_verification_code(code: str) -> str:
    """Hash a verification code for storage."""
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def verify_verification_code(code: str, code_hash: str) -> bool:
    """Constant-time comparison of a submitted code against its stored hash."""
    return hmac.compare_digest(hash_verification_code(code), code_hash)


def generate_refresh_token() -> str:
    """Generate an opaque, URL-safe refresh token."""
    return secrets.token_urlsafe(_REFRESH_TOKEN_BYTES)


def hash_refresh_token(token: str) -> str:
    """Hash a refresh token for storage and lookup."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

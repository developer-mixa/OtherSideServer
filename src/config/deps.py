"""FastAPI dependencies."""

from __future__ import annotations

from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

bearer_scheme = HTTPBearer(auto_error=False)


def bearer_token(credentials: HTTPAuthorizationCredentials | None) -> str | None:
    """The raw token from an ``Authorization: Bearer`` header, if any.

    Validation (signature, expiry, session revocation) is done by
    ``AuthenticateAccessTokenUseCase``, which needs the database and so cannot live here.
    """
    return credentials.credentials if credentials is not None else None

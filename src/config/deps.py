"""FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config.security import get_user_id_from_token
from domain.exceptions import AuthenticationError

bearer_scheme = HTTPBearer(auto_error=False)


def resolve_user_id(credentials: HTTPAuthorizationCredentials | None) -> UUID:
    """Extract user ID from Bearer credentials."""
    if credentials is None:
        raise AuthenticationError("Not authenticated", code="not_authenticated")
    return get_user_id_from_token(credentials.credentials)


async def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> UUID:
    """Extract authenticated user ID from Bearer token."""
    return resolve_user_id(credentials)

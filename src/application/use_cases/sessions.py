"""Session lifecycle use cases: refresh token rotation, logout, password change."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from application.dtos import AuthTokenDTO
from application.interfaces import PasswordHasherProtocol, UnitOfWorkProtocol
from config.security import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_refresh_token,
    user_id_from_claims,
)
from config.settings import settings
from domain.entities import RefreshToken
from domain.exceptions import (
    AuthenticationError,
    AuthorizationError,
    EntityNotFoundError,
    ValidationError,
)
from domain.value_objects import Password

logger = logging.getLogger(__name__)

SESSION_ID_CLAIM = "sid"


async def issue_token_pair(
    uow: UnitOfWorkProtocol,
    user_id: UUID,
    now: datetime,
    family_id: UUID | None = None,
) -> tuple[AuthTokenDTO, RefreshToken]:
    """Create an access token and persist a new refresh token (the caller commits).

    Without ``family_id`` the refresh token starts a new session (login); with it, the
    token continues an existing session (rotation).
    """
    raw_refresh_token = generate_refresh_token()
    refresh_token = RefreshToken.issue(
        user_id=user_id,
        token_hash=hash_refresh_token(raw_refresh_token),
        now=now,
        ttl=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        family_id=family_id,
    )
    await uow.refresh_tokens.add(refresh_token)
    access_ttl = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    # `sid` ties the access token to its session, so revoking the session (logout,
    # password change, block, reuse detection) disables the access token immediately.
    claims = {"sub": str(user_id), SESSION_ID_CLAIM: str(refresh_token.family_id)}
    tokens = AuthTokenDTO(
        access_token=create_access_token(claims, expires_delta=access_ttl),
        refresh_token=raw_refresh_token,
        expires_in=int(access_ttl.total_seconds()),
    )
    return tokens, refresh_token


class AuthenticateAccessTokenUseCase:
    """Resolve the caller of a request from its access token, honoring session revocation.

    A JWT alone cannot be revoked; the ``sid`` claim lets every authenticated request
    check that the session it belongs to has not been ended.
    """

    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(self, access_token: str | None) -> UUID:
        if access_token is None:
            raise AuthenticationError("Not authenticated", code="not_authenticated")
        claims = decode_access_token(access_token)
        user_id = user_id_from_claims(claims)

        raw_session_id = claims.get(SESSION_ID_CLAIM)
        if raw_session_id is None:
            # Issued before sessions existed: still bounded by its `exp`, so it is accepted
            # until it expires rather than logging every user out on deploy.
            return user_id
        try:
            session_id = UUID(str(raw_session_id))
        except ValueError as exc:
            raise AuthenticationError("Invalid or expired token", code="token_invalid") from exc

        async with self._uow:
            if await self._uow.refresh_tokens.is_family_active(session_id):
                return user_id
            # Keep the established 403 for blocked users (block revokes their sessions,
            # so this is the path they now take); everyone else must log in again.
            user = await self._uow.users.get_by_id(user_id)
            if user is not None and user.is_blocked:
                raise AuthorizationError("User is blocked", code="user_blocked")
            raise AuthenticationError("Session has been revoked", code="session_revoked")


class RefreshTokensUseCase:
    """Exchange a refresh token for a new access/refresh pair, revoking the old one."""

    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(self, raw_refresh_token: str) -> AuthTokenDTO:
        now = datetime.now(timezone.utc)

        async with self._uow:
            token = await self._uow.refresh_tokens.get_by_hash(
                hash_refresh_token(raw_refresh_token), for_update=True
            )
            if token is None:
                raise AuthenticationError("Invalid refresh token", code="refresh_token_invalid")

            if token.is_revoked:
                # A rotated-away token is being replayed: either the client or an attacker
                # holds a stolen copy, and we cannot tell which. Kill the whole session so
                # the stolen chain dies too; the legitimate user simply logs in again.
                revoked = await self._uow.refresh_tokens.revoke_family(token.family_id, now)
                await self._uow.commit()
                logger.warning(
                    "Refresh token reuse detected: user_id=%s family_id=%s, revoked %d token(s)",
                    token.user_id,
                    token.family_id,
                    revoked,
                )
                raise AuthenticationError(
                    "Refresh token has already been used", code="refresh_token_reused"
                )

            if token.is_expired(now):
                raise AuthenticationError("Refresh token has expired", code="refresh_token_expired")

            user = await self._uow.users.get_by_id(token.user_id)
            if user is None or user.is_blocked:
                await self._uow.refresh_tokens.revoke_family(token.family_id, now)
                await self._uow.commit()
                if user is None:
                    raise AuthenticationError("Invalid refresh token", code="refresh_token_invalid")
                raise AuthorizationError("User is blocked", code="user_blocked")

            tokens, new_token = await issue_token_pair(
                self._uow, user.id, now, family_id=token.family_id
            )
            await self._uow.refresh_tokens.revoke(token.id, now, replaced_by_id=new_token.id)
            await self._uow.commit()
            return tokens


class LogoutUseCase:
    """End the session the refresh token belongs to.

    Always succeeds, even for unknown or already-revoked tokens: logout is idempotent and
    must not reveal whether a token string is valid.
    """

    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(self, raw_refresh_token: str) -> None:
        async with self._uow:
            token = await self._uow.refresh_tokens.get_by_hash(
                hash_refresh_token(raw_refresh_token)
            )
            if token is None:
                return
            await self._uow.refresh_tokens.revoke_family(
                token.family_id, datetime.now(timezone.utc)
            )
            await self._uow.commit()


class ChangePasswordUseCase:
    """Change the caller's password and sign out every session they have."""

    def __init__(self, uow: UnitOfWorkProtocol, password_hasher: PasswordHasherProtocol) -> None:
        self._uow = uow
        self._password_hasher = password_hasher

    async def execute(self, user_id: UUID, current_password: str, new_password: str) -> None:
        Password(new_password)
        if new_password == current_password:
            raise ValidationError(
                "New password must differ from the current one", code="password_unchanged"
            )

        async with self._uow:
            user = await self._uow.users.get_by_id(user_id)
            if user is None:
                raise EntityNotFoundError("User", user_id)
            if user.is_blocked:
                raise AuthorizationError("User is blocked", code="user_blocked")

            check = await self._password_hasher.verify(current_password, user.password_hash)
            if not check.is_valid:
                # 422, not 401: the caller *is* authenticated, and a 401 here would make
                # clients drop their session as if the access token had expired.
                raise ValidationError(
                    "Current password is incorrect", code="current_password_invalid"
                )

            user.password_hash = await self._password_hasher.hash(new_password)
            await self._uow.users.update(user)
            # Whoever learned the old password may already hold a refresh token; changing
            # it is pointless unless those sessions end too.
            await self._uow.refresh_tokens.revoke_all_for_user(user.id, datetime.now(timezone.utc))
            await self._uow.commit()

"""Password hashing: Argon2id via pwdlib, with transparent upgrade of legacy bcrypt hashes."""

from __future__ import annotations

import logging

import anyio
import anyio.to_thread
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher

from application.dtos import PasswordVerificationDTO

logger = logging.getLogger(__name__)

# Hashed once per hasher instance and verified against when the account does not exist,
# so a login for an unknown email spends the same time as one for a real user.
_TIMING_EQUALIZER_PASSWORD = "timing-attack-equalizer"


class PwdlibPasswordHasher:
    """Argon2id hasher that still verifies (and re-hashes) bcrypt hashes from passlib.

    Hashing is CPU- and memory-bound and would block the event loop, so every call runs
    in a worker thread. A dedicated limiter caps how many hashes run at once: each Argon2
    computation allocates ``memory_cost_kib`` of RAM, and anyio's default thread pool
    (40 threads) times that is enough to OOM a small instance under a login burst.
    """

    def __init__(
        self,
        *,
        time_cost: int,
        memory_cost_kib: int,
        parallelism: int,
        max_concurrency: int,
    ) -> None:
        # The first hasher is the one new hashes are made with; the rest are only accepted
        # for verification, and verify_and_update() re-hashes them with the first one.
        self._password_hash = PasswordHash(
            (
                Argon2Hasher(
                    time_cost=time_cost,
                    memory_cost=memory_cost_kib,
                    parallelism=parallelism,
                ),
                BcryptHasher(),
            )
        )
        self._max_concurrency = max_concurrency
        self._limiter: anyio.CapacityLimiter | None = None
        self._dummy_hash = self._password_hash.hash(_TIMING_EQUALIZER_PASSWORD)

    def _get_limiter(self) -> anyio.CapacityLimiter:
        # Created lazily: a limiter is bound to the event loop it is first used on, and
        # this object is built before the loop exists (DI container, module import).
        if self._limiter is None:
            self._limiter = anyio.CapacityLimiter(self._max_concurrency)
        return self._limiter

    def hash_sync(self, password: str) -> str:
        """Hash on the calling thread. Only for scripts and tests, never inside the event loop."""
        return self._password_hash.hash(password)

    async def hash(self, password: str) -> str:
        return await anyio.to_thread.run_sync(
            self._password_hash.hash, password, limiter=self._get_limiter()
        )

    async def verify(self, password: str, password_hash: str) -> PasswordVerificationDTO:
        try:
            is_valid, updated_hash = await anyio.to_thread.run_sync(
                self._password_hash.verify_and_update,
                password,
                password_hash,
                limiter=self._get_limiter(),
            )
        except UnknownHashError:
            # A corrupted or foreign hash format must read as "wrong password", not as a
            # 500 — but it is worth knowing about, since that account can never log in.
            logger.warning("Stored password hash has an unrecognized format")
            return PasswordVerificationDTO(is_valid=False)
        return PasswordVerificationDTO(is_valid=is_valid, updated_hash=updated_hash)

    async def dummy_verify(self, password: str) -> None:
        await self.verify(password, self._dummy_hash)

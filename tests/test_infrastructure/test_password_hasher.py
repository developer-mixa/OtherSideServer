"""Argon2id password hasher tests, including the bcrypt → Argon2id upgrade path."""

import asyncio
import threading
import time

import bcrypt
from tests.conftest import make_test_password_hasher

from config.ioc.providers import build_password_hasher
from config.settings import settings
from infrastructure.security.passwords import PwdlibPasswordHasher


def _legacy_bcrypt_hash(password: str) -> str:
    """A hash in exactly the format passlib's CryptContext(schemes=["bcrypt"]) stored."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=4, prefix=b"2b")).decode()


class TestPwdlibPasswordHasher:
    async def test_hash_is_argon2id_and_verifies(self) -> None:
        hasher = make_test_password_hasher()
        hashed = await hasher.hash("password123")

        assert hashed.startswith("$argon2id$")
        assert (await hasher.verify("password123", hashed)).is_valid is True
        assert (await hasher.verify("wrong-password", hashed)).is_valid is False

    async def test_current_hash_needs_no_update(self) -> None:
        hasher = make_test_password_hasher()
        check = await hasher.verify("password123", await hasher.hash("password123"))
        assert check.updated_hash is None

    async def test_legacy_bcrypt_hash_verifies_and_is_upgraded(self) -> None:
        hasher = make_test_password_hasher()
        legacy = _legacy_bcrypt_hash("password123")

        check = await hasher.verify("password123", legacy)

        assert check.is_valid is True
        assert check.updated_hash is not None
        assert check.updated_hash.startswith("$argon2id$")
        assert (await hasher.verify("password123", check.updated_hash)).updated_hash is None

    async def test_wrong_password_against_bcrypt_is_not_upgraded(self) -> None:
        hasher = make_test_password_hasher()
        check = await hasher.verify("wrong-password", _legacy_bcrypt_hash("password123"))
        assert check.is_valid is False
        assert check.updated_hash is None

    async def test_stronger_parameters_trigger_rehash(self) -> None:
        weak = make_test_password_hasher()
        stronger = PwdlibPasswordHasher(
            time_cost=2, memory_cost_kib=2048, parallelism=1, max_concurrency=1
        )
        check = await stronger.verify("password123", await weak.hash("password123"))
        assert check.is_valid is True
        assert check.updated_hash is not None

    async def test_unknown_hash_format_is_a_failed_check_not_an_error(self) -> None:
        hasher = make_test_password_hasher()
        check = await hasher.verify("password123", "plaintext-or-garbage")
        assert check.is_valid is False
        assert check.updated_hash is None

    async def test_dummy_verify_completes(self) -> None:
        await make_test_password_hasher().dummy_verify("whatever")

    async def test_concurrency_is_capped_by_limiter(self) -> None:
        hasher = PwdlibPasswordHasher(
            time_cost=1, memory_cost_kib=1024, parallelism=1, max_concurrency=2
        )
        lock = threading.Lock()
        running = peak = 0

        def slow_hash(password: str) -> str:
            nonlocal running, peak
            with lock:
                running += 1
                peak = max(peak, running)
            time.sleep(0.05)
            with lock:
                running -= 1
            return password

        hasher._password_hash.hash = slow_hash  # type: ignore[method-assign]
        await asyncio.gather(*(hasher.hash(f"password-{i}") for i in range(8)))

        assert peak == 2

    async def test_hashing_does_not_block_the_event_loop(self) -> None:
        hasher = make_test_password_hasher()

        def blocking_hash(password: str) -> str:
            time.sleep(0.2)  # stands in for a CPU-bound Argon2 computation
            return password

        hasher._password_hash.hash = blocking_hash  # type: ignore[method-assign]
        ticks = 0

        async def ticker() -> None:
            nonlocal ticks
            while True:
                await asyncio.sleep(0.01)
                ticks += 1

        task = asyncio.create_task(ticker())
        await hasher.hash("password123")
        task.cancel()

        assert ticks >= 5

    def test_hash_sync_produces_verifiable_hash(self) -> None:
        hasher = make_test_password_hasher()
        hashed = hasher.hash_sync("password123")
        assert asyncio.run(hasher.verify("password123", hashed)).is_valid is True


class TestBuildPasswordHasher:
    async def test_uses_settings_parameters(self) -> None:
        hashed = await build_password_hasher().hash("password123")
        assert f"m={settings.PASSWORD_HASH_MEMORY_COST_KIB}" in hashed
        assert f"t={settings.PASSWORD_HASH_TIME_COST}" in hashed
        assert f"p={settings.PASSWORD_HASH_PARALLELISM}" in hashed

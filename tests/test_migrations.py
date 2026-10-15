"""Every Alembic migration must apply and roll back cleanly on a real PostgreSQL."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import make_url, text
from sqlalchemy.ext.asyncio import create_async_engine

from config.settings import settings
from tests.conftest import PROJECT_ROOT


async def _execute_autocommit(url: str, statement: str) -> None:
    # CREATE/DROP DATABASE cannot run inside a transaction block.
    engine = create_async_engine(url, isolation_level="AUTOCOMMIT")
    try:
        async with engine.connect() as connection:
            await connection.execute(text(statement))
    finally:
        await engine.dispose()


@pytest.fixture
def scratch_database_url(database_url: str) -> Iterator[str]:
    """A throwaway database next to the session one, so downgrading cannot hurt other tests."""
    name = f"migrations_{uuid4().hex[:12]}"
    asyncio.run(_execute_autocommit(database_url, f'CREATE DATABASE "{name}"'))
    original = settings.DATABASE_URL
    scratch_url = make_url(database_url).set(database=name).render_as_string(hide_password=False)
    settings.DATABASE_URL = scratch_url
    try:
        yield scratch_url
    finally:
        settings.DATABASE_URL = original
        asyncio.run(_execute_autocommit(database_url, f'DROP DATABASE "{name}" WITH (FORCE)'))


def _alembic_config() -> Config:
    config = Config()
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    return config


def test_upgrade_downgrade_upgrade_round_trip(scratch_database_url: str) -> None:
    config = _alembic_config()
    command.upgrade(config, "head")
    command.downgrade(config, "base")
    command.upgrade(config, "head")


def test_each_migration_downgrades_one_step(scratch_database_url: str) -> None:
    """Stepwise: catches a downgrade that only works when run as part of a full rollback."""
    config = _alembic_config()
    revisions = list(reversed(list(ScriptDirectory.from_config(config).walk_revisions())))
    for revision in revisions:
        command.upgrade(config, revision.revision)
        command.downgrade(config, "-1")
        command.upgrade(config, revision.revision)


def test_history_is_linear() -> None:
    heads = ScriptDirectory.from_config(_alembic_config()).get_heads()
    assert len(heads) == 1, f"multiple Alembic heads: {heads}"

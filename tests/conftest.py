"""Test database setup.

Tests use a separate database, `<DB_NAME>_test`, in the same Postgres as development.
It is recreated and migrated once per test run; every test runs inside a transaction
that is rolled back afterwards, so tests do not see each other's data.
"""

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from bot.config import DatabaseSettings

ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"


async def _recreate_database(settings: DatabaseSettings, name: str) -> None:
    # CREATE/DROP DATABASE cannot run inside a transaction, hence AUTOCOMMIT.
    maintenance = settings.model_copy(update={"db_name": "postgres"})
    engine = create_async_engine(maintenance.url, isolation_level="AUTOCOMMIT")
    async with engine.connect() as connection:
        await connection.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        await connection.execute(text(f'CREATE DATABASE "{name}"'))
    await engine.dispose()


@pytest.fixture(scope="session")
def database_url() -> str:
    settings = DatabaseSettings()
    test_settings = settings.model_copy(update={"db_name": f"{settings.db_name}_test"})
    asyncio.run(_recreate_database(settings, test_settings.db_name))

    config = Config(ALEMBIC_INI)
    config.set_main_option("sqlalchemy.url", test_settings.url.replace("%", "%%"))
    command.upgrade(config, "head")
    return test_settings.url


@pytest.fixture
async def session(database_url: str) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(database_url, poolclass=NullPool)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        # Commits made by the code under test become savepoints inside this transaction.
        session = AsyncSession(
            bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()
    await engine.dispose()

"""Alembic migrations against real Postgres.

PostgreSQL DDL is transactional, so these run inside the per-test transaction from the
`connection` fixture and are rolled back, leaving the shared schema untouched.
"""

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect

from todoapp.database import Base


async def test_models_match_migrations(connection):
    """Fails when a model changed without a matching `alembic revision --autogenerate`."""

    def diff(sync_conn):
        return compare_metadata(MigrationContext.configure(sync_conn), Base.metadata)

    assert await connection.run_sync(diff) == []


async def test_downgrade_and_upgrade_round_trip(connection, alembic_config):
    def round_trip(sync_conn):
        config = alembic_config(sync_conn)
        command.downgrade(config, "base")
        after_downgrade = set(inspect(sync_conn).get_table_names())
        command.upgrade(config, "head")
        after_upgrade = set(inspect(sync_conn).get_table_names())
        return after_downgrade, after_upgrade

    after_downgrade, after_upgrade = await connection.run_sync(round_trip)

    assert after_downgrade <= {"alembic_version"}
    assert {"users", "todos"} <= after_upgrade

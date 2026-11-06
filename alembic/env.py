import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from todoapp import models  # noqa: F401  (imports the models so their tables are registered)
from todoapp.config import settings
from todoapp.database import Base

# The Alembic Config object, giving access to the values in alembic.ini.
config = context.config

# A caller (the integration tests) can pass an open connection to migrate, instead of
# Alembic connecting to settings.database_url itself.
external_connection = config.attributes.get("connection")

# Set up Python logging from alembic.ini, unless a caller (with its own logging) runs us.
if config.config_file_name is not None and external_connection is None:
    fileConfig(config.config_file_name)

# The models' tables, compared against the database by `alembic revision --autogenerate`.
target_metadata = Base.metadata

# The database URL comes from the app settings (DATABASE_URL / .env), never alembic.ini,
# so credentials stay out of the repo and the app and migrations use the same database.
database_url = settings.database_url


def run_migrations_offline() -> None:
    """Emit migration SQL to stdout (`alembic upgrade head --sql`) without connecting."""
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations against the database, using the app's async driver."""
    engine = create_async_engine(database_url, poolclass=pool.NullPool)

    # Alembic's migration API is synchronous; run_sync runs it on the async connection.
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await engine.dispose()


if external_connection is not None:
    do_run_migrations(external_connection)
elif context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())

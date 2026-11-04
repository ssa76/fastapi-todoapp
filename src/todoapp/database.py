from typing import Annotated

from fastapi import Depends
from sqlalchemy import String, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from todoapp.config import settings

engine = create_async_engine(settings.database_url)


if engine.dialect.name == "sqlite":

    @event.listens_for(engine.sync_engine, "connect")
    def _enable_sqlite_fks(dbapi_conn, _):
        # SQLite ignores foreign keys unless enabled on each new connection.
        # (Postgres always enforces them, and would reject this command.)
        dbapi_conn.execute("PRAGMA foreign_keys=ON")


# expire_on_commit=False: attributes stay readable after commit without an implicit
# (non-awaitable) reload, which would raise MissingGreenlet.
SessionLocal = async_sessionmaker(engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    # Map `str` columns to VARCHAR(255) instead of unbounded VARCHAR.
    type_annotation_map = {str: String(255)}


async def get_db():
    # Closing the session rolls back any uncommitted work; errors propagate to FastAPI.
    async with SessionLocal() as db:
        yield db


DbSession = Annotated[AsyncSession, Depends(get_db)]

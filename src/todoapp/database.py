from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy import event

SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./todosapp.db"

engine = create_async_engine(SQLALCHEMY_DATABASE_URL)

# expire_on_commit=False: attributes stay readable after commit without an implicit
# (non-awaitable) reload, which would raise MissingGreenlet.
SessionLocal = async_sessionmaker(engine, autoflush=False, expire_on_commit=False)

Base = declarative_base()


async def get_db():
    # Closing the session rolls back any uncommitted work; errors propagate to FastAPI.
    async with SessionLocal() as db:
        yield db


DbSession = Annotated[AsyncSession, Depends(get_db)]


@event.listens_for(engine.sync_engine, "connect")
def _enable_sqlite(dbapi_conn, _):
    dbapi_conn.execute("PRAGMA foreign_keys=ON")

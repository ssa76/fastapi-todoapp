from typing import Annotated

from fastapi import Depends
from sqlalchemy import String
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from todoapp.config import settings

engine = create_async_engine(settings.database_url)

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

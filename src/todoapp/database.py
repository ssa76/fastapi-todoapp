from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./todos.db"

engine = create_async_engine(SQLALCHEMY_DATABASE_URL)

# expire_on_commit=False: attributes stay readable after commit without an implicit
# (non-awaitable) reload, which would raise MissingGreenlet.
SessionLocal = async_sessionmaker(engine, autoflush=False, expire_on_commit=False)

Base = declarative_base()

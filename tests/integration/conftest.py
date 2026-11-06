"""Fixtures for integration tests against a real PostgreSQL in a throwaway container.

Lifetimes:
- one Postgres container and one engine for the whole test run, migrated once with Alembic;
- per test, a connection inside an outer transaction that is rolled back afterwards.
  The app's own commit()/rollback() calls only touch savepoints inside it
  (join_transaction_mode="create_savepoint"), so every test starts with empty tables.
"""

import os
import shutil
import subprocess
from collections.abc import AsyncIterator, Callable, Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import Connection
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from todoapp.database import get_db
from todoapp.main import app
from todoapp.models import Todos, Users
from todoapp.routers.auth import create_access_token
from todoapp.security import _hash

PROJECT_ROOT = Path(__file__).resolve().parents[2]
POSTGRES_IMAGE = "docker.io/library/postgres:18"  # same image as compose.postgres.yaml
PASSWORD = "correct-horse-battery"


def _podman(*args: str) -> str | None:
    result = subprocess.run(["podman", *args], capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 and result.stdout.strip() else None


def _podman_socket_url() -> str:
    """URL of Podman's API socket, which serves the Docker-compatible API Testcontainers uses."""
    if shutil.which("podman") is None:
        pytest.fail("Integration tests need Podman: `podman` is not on PATH.")
    # macOS / Windows: the API socket forwarded from the running `podman machine`.
    machine_socket = _podman(
        "machine", "inspect", "--format", "{{.ConnectionInfo.PodmanSocket.Path}}"
    )
    if machine_socket:
        return f"unix://{machine_socket}"
    # Linux: Podman runs natively; its API socket (needs `systemctl --user start podman.socket`).
    local_socket = _podman("info", "--format", "{{.Host.RemoteSocket.Path}}")
    if local_socket:
        return local_socket if "://" in local_socket else f"unix://{local_socket}"
    pytest.fail(
        "Can't find Podman's API socket. On macOS start the VM with `podman machine start`; "
        "on Linux run `systemctl --user start podman.socket`."
    )


def _configure_testcontainers_for_podman() -> None:
    # Testcontainers reads the API location from DOCKER_HOST; it always points at Podman.
    os.environ["DOCKER_HOST"] = _podman_socket_url()
    # Ryuk (Testcontainers' reaper container) needs privileges rootless Podman doesn't give
    # it. The fixture below stops and removes the Postgres container itself.
    os.environ["TESTCONTAINERS_RYUK_DISABLED"] = "true"


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    _configure_testcontainers_for_podman()
    # Imported here so the env vars above are set before Testcontainers reads them.
    # (`docker` is only the Python client library; it talks to Podman's compatible API.)
    from docker.errors import DockerException
    from testcontainers.community.postgres import PostgresContainer

    try:
        container = PostgresContainer(POSTGRES_IMAGE, driver="asyncpg").start()
    except DockerException as exc:
        pytest.fail(f"Couldn't start PostgreSQL on Podman ({os.environ['DOCKER_HOST']}): {exc}")
    try:
        yield container.get_connection_url()
    finally:
        container.stop()


def make_alembic_config(connection: Connection) -> Config:
    """Alembic config that migrates `connection` (see the hook in alembic/env.py)."""
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.attributes["connection"] = connection
    return config


@pytest.fixture(scope="session")
def alembic_config() -> Callable[[Connection], Config]:
    return make_alembic_config


@pytest.fixture(scope="session")
async def engine(postgres_url: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(postgres_url, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(lambda c: command.upgrade(make_alembic_config(c), "head"))
    yield engine
    await engine.dispose()


@pytest.fixture
async def connection(engine: AsyncEngine) -> AsyncIterator[AsyncConnection]:
    """A connection inside a transaction that is always rolled back after the test."""
    async with engine.connect() as conn:
        transaction = await conn.begin()
        try:
            yield conn
        finally:
            await transaction.rollback()


@pytest.fixture
async def db_session(connection: AsyncConnection) -> AsyncIterator[AsyncSession]:
    # Same options as the app's SessionLocal, plus savepoints so the app's commits
    # don't end the outer (rolled-back) transaction.
    session = AsyncSession(
        bind=connection,
        autoflush=False,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    try:
        yield session
    finally:
        await session.close()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    # ASGITransport runs the app on the test's event loop. TestClient would use its own
    # loop in another thread, which asyncpg connections can't be shared with.
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture(scope="session")
def password() -> str:
    """Plain-text password of every user made by `make_user`."""
    return PASSWORD


@pytest.fixture(scope="session")
def password_hash() -> str:
    # bcrypt takes ~150 ms per hash, so hash the shared test password once per run.
    return _hash(PASSWORD.encode())


@pytest.fixture
def make_user(db_session: AsyncSession, password_hash: str) -> Callable:
    """Factory: insert a user directly (no HTTP round trip); its password is PASSWORD."""

    async def _make_user(username: str = "alice", role: str = "user", **fields) -> Users:
        user = Users(
            username=username,
            email=f"{username}@example.com",
            first_name=username.title(),
            last_name="Tester",
            hashed_password=password_hash,
            role=role,
            **fields,
        )
        db_session.add(user)
        await db_session.commit()
        return user

    return _make_user


@pytest.fixture
def make_todo(db_session: AsyncSession) -> Callable:
    async def _make_todo(owner: Users, title: str = "Buy milk", **fields) -> Todos:
        values = {"description": "From the shop", "priority": 3, **fields}
        todo = Todos(title=title, owner_id=owner.id, **values)
        db_session.add(todo)
        await db_session.commit()
        return todo

    return _make_todo


@pytest.fixture
def auth_headers() -> Callable[[Users], dict[str, str]]:
    """Factory: Authorization header with a valid token for the given user."""

    def _auth_headers(user: Users) -> dict[str, str]:
        return {"Authorization": f"Bearer {create_access_token(user)}"}

    return _auth_headers


@pytest.fixture
async def user(make_user) -> Users:
    return await make_user("alice")


@pytest.fixture
async def admin(make_user) -> Users:
    return await make_user("root", role="admin")

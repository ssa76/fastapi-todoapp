import os
from pathlib import Path

import pytest

# `todoapp.config` builds Settings() and `todoapp.database` builds the engine as soon as
# they're imported, which happens while pytest collects test modules, before any fixture
# runs. Give them values here so the tests don't depend on a local .env. The placeholder
# URL is never connected to: integration tests swap the app's `get_db` for a session on
# the Testcontainers database (see tests/integration/conftest.py).
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production-use-0123456789")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://unused:unused@localhost:1/unused")

INTEGRATION_DIR = Path(__file__).parent / "integration"


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    # Everything under tests/integration/ gets the marker, so `-m "not integration"`
    # runs the fast tests without a container runtime.
    for item in items:
        if INTEGRATION_DIR in item.path.parents:
            item.add_marker(pytest.mark.integration)

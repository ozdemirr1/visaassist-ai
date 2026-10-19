"""Integration tests against a real PostgreSQL server.

They run only when RUN_INTEGRATION=1, so `uv run pytest` works without a
database. CI sets the variable and provides PostgreSQL as a service.
"""

import os

import pytest
from sqlalchemy import text

from app.db import database_is_reachable, get_engine

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION") != "1",
    reason="set RUN_INTEGRATION=1 and start the database to run",
)


def test_database_is_reachable() -> None:
    assert database_is_reachable() is True


def test_pgvector_extension_is_available() -> None:
    with get_engine().connect() as connection:
        available = connection.execute(
            text("SELECT 1 FROM pg_available_extensions WHERE name = 'vector'")
        ).scalar()

    assert available == 1

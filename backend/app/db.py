"""Database engine and connectivity check."""

from functools import lru_cache

from sqlalchemy import Engine, create_engine, text

from app.config import get_settings


@lru_cache
def get_engine() -> Engine:
    """Create the SQLAlchemy engine lazily, on first use, and reuse it."""
    return create_engine(
        get_settings().database_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 3},
    )


def database_is_reachable() -> bool:
    """Return True if a trivial query succeeds.

    Any failure (missing settings, refused connection, wrong password) means
    the service is not ready, so it is reported as False instead of raising.
    """
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        return False
    return True

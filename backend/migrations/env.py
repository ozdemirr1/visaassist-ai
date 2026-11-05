"""Alembic environment: migrations run against DATABASE_URL from the application settings."""

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import get_settings
from app.models import Base

config = context.config
target_metadata = Base.metadata


def database_url() -> str:
    # An explicitly configured URL (e.g. from tests) wins over the settings.
    return config.get_main_option("sqlalchemy.url") or get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(url=database_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = engine_from_config(
        {"sqlalchemy.url": database_url()}, prefix="sqlalchemy.", poolclass=pool.NullPool
    )
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

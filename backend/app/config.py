"""Application settings, read from environment variables and `.env` files."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed settings; every field can be overridden by an environment variable.

    `.env` is looked up in the current directory and in its parent, so the
    repository-root `.env` is found when commands run from `backend/`.
    """

    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    # Required on purpose: there is no safe default for credentials.
    database_url: str


@lru_cache
def get_settings() -> Settings:
    """Load settings once per process."""
    return Settings()

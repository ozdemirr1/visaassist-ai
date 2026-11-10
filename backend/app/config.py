"""Application settings, read from environment variables and `.env` files."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed settings; every field can be overridden by an environment variable.

    `.env` is looked up in the current directory and in its parent, so the
    repository-root `.env` is found when commands run from `backend/`.
    """

    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    # Required on purpose: there is no safe default for credentials.
    database_url: str

    # Session cookie (ADR 0004). Secure by default; set COOKIE_SECURE=false only for a browser
    # that refuses Secure cookies on http://localhost during development.
    cookie_secure: bool = True

    # Uploaded documents (ADR 0005). The master key wraps every document's own key; without it
    # the API does not start. Generate one with `python -m app.storage.new_key`.
    document_master_key: str | None = None
    document_key_id: str = "k1"
    storage_dir: Path = Path(__file__).resolve().parents[2] / "storage"


@lru_cache
def get_settings() -> Settings:
    """Load settings once per process."""
    return Settings()

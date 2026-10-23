"""Load and validate the official source registry in `data/sources.yaml`."""

from datetime import date
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REGISTRY = REPO_ROOT / "data" / "sources.yaml"


class Source(BaseModel):
    """One official page or document that requirements are taken from."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")
    title: str = Field(min_length=1)
    publisher: str = Field(min_length=1)
    layer: Literal["eu", "national"]
    destination: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    url: HttpUrl
    format: Literal["html", "pdf"]
    source_date: date | None = None
    reviewed_on: date

    @field_validator("url")
    @classmethod
    def url_uses_https(cls, value: HttpUrl) -> HttpUrl:
        if value.scheme != "https":
            raise ValueError("official sources must be fetched over HTTPS")
        return value

    @model_validator(mode="after")
    def destination_matches_layer(self) -> "Source":
        if self.layer == "national" and self.destination is None:
            raise ValueError("a national source needs a destination country code")
        if self.layer == "eu" and self.destination is not None:
            raise ValueError("an EU source applies to every destination; leave destination empty")
        return self


class Registry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sources: list[Source] = Field(min_length=1)

    @model_validator(mode="after")
    def ids_are_unique(self) -> "Registry":
        ids = [source.id for source in self.sources]
        duplicates = sorted({i for i in ids if ids.count(i) > 1})
        if duplicates:
            raise ValueError(f"duplicate source ids: {', '.join(duplicates)}")
        return self

    def get(self, source_id: str) -> Source:
        for source in self.sources:
            if source.id == source_id:
                return source
        raise KeyError(source_id)


def load_registry(path: Path = DEFAULT_REGISTRY) -> Registry:
    """Read the YAML registry and validate it."""
    with path.open(encoding="utf-8") as handle:
        return Registry.model_validate(yaml.safe_load(handle))

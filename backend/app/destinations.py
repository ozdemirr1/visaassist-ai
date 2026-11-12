"""Facts about applying to each destination (`data/destinations.yaml`), each with its source.

Read from the file on request, like the source registry: the content is small, changes with the
repository and needs no database.
"""

from datetime import date
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import Field, model_validator

from app.requirements.schema import Citation, Id, LocalizedText, Strict
from app.sources.registry import REPO_ROOT, Registry, load_registry

DEFAULT_DESTINATIONS = REPO_ROOT / "data" / "destinations.yaml"


class Fact(Strict):
    id: Id
    title: LocalizedText
    text: LocalizedText
    source: Citation


class Destination(Strict):
    id: str = Field(pattern=r"^[A-Z]{2}$")
    schengen: bool
    facts: list[Fact] = Field(min_length=1)


class DestinationData(Strict):
    checked_on: date
    destinations: list[Destination] = Field(min_length=1)

    @model_validator(mode="after")
    def ids_are_unique(self) -> "DestinationData":
        ids = [d.id for d in self.destinations]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate destination ids")
        for destination in self.destinations:
            fact_ids = [f.id for f in destination.facts]
            if len(set(fact_ids)) != len(fact_ids):
                raise ValueError(f"duplicate fact ids for {destination.id}")
        return self


def problems(data: DestinationData, registry: Registry) -> list[str]:
    """Facts whose source is unknown or belongs to another destination."""
    known = {source.id: source for source in registry.sources}
    found = []
    for destination in data.destinations:
        for fact in destination.facts:
            source = known.get(fact.source.source_id)
            if source is None:
                found.append(f"{destination.id}.{fact.id}: unknown source {fact.source.source_id}")
            elif source.destination not in (None, destination.id):
                found.append(f"{destination.id}.{fact.id}: source is about {source.destination}")
    return found


def load_destinations(
    path: Path = DEFAULT_DESTINATIONS, registry: Registry | None = None
) -> DestinationData:
    with path.open(encoding="utf-8") as handle:
        data = DestinationData.model_validate(yaml.safe_load(handle))
    found = problems(data, registry or load_registry())
    if found:
        raise ValueError("invalid destination data:\n- " + "\n- ".join(found))
    return data


@lru_cache
def get_destinations() -> DestinationData:
    return load_destinations()

"""Discovery page data: what to know before applying to a destination, with sources (FR-01)."""

from datetime import date
from functools import lru_cache
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.checklist import Citation
from app.destinations import get_destinations
from app.sources.registry import Registry, load_registry

router = APIRouter(tags=["destinations"])
Language = Literal["tr", "en"]


class FactOut(BaseModel):
    id: str
    title: str
    text: str
    source: Citation


class DestinationOut(BaseModel):
    id: str
    schengen: bool
    facts: list[FactOut]


class DestinationsOut(BaseModel):
    checked_on: date
    destinations: list[DestinationOut]


@lru_cache
def _registry() -> Registry:
    return load_registry()


@router.get("/destinations", response_model=DestinationsOut)
def list_destinations(lang: Language = "tr") -> DestinationsOut:
    """The pilot destinations with the practical facts of applying from Türkiye."""
    data = get_destinations()
    registry = _registry()

    def cite(fact) -> Citation:
        source = registry.get(fact.source.source_id)
        return Citation(
            source_id=source.id,
            title=source.title,
            publisher=source.publisher,
            url=str(source.url),
            section=fact.source.section,
            passage=fact.source.passage,
            basis=fact.source.basis,
        )

    return DestinationsOut(
        checked_on=data.checked_on,
        destinations=[
            DestinationOut(
                id=destination.id,
                schengen=destination.schengen,
                facts=[
                    FactOut(
                        id=fact.id,
                        title=getattr(fact.title, lang),
                        text=getattr(fact.text, lang),
                        source=cite(fact),
                    )
                    for fact in destination.facts
                ],
            )
            for destination in data.destinations
        ],
    )

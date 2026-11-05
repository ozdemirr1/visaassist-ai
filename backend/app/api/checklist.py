"""Personalised checklist (FR-02): the documents a profile needs for a destination, with sources."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import any_, or_, select
from sqlalchemy.orm import Session

from app import models
from app.db import get_session

router = APIRouter(tags=["checklist"])

Language = Literal["tr", "en"]
Profile = Literal["employed", "student"]


class Citation(BaseModel):
    source_id: str
    title: str
    publisher: str
    url: str
    section: str
    passage: str
    basis: Literal["stated", "derived"]


class DocumentRef(BaseModel):
    id: str
    title: str
    multiple: bool


class ChecklistItem(BaseModel):
    id: str
    layer: Literal["eu", "national"]
    document: DocumentRef
    submit_as: str
    note: str | None
    source: Citation


class RuleSummary(BaseModel):
    id: str
    title: str
    severity: Literal["error", "warning"]
    kind: str
    source: Citation


class Translation(BaseModel):
    required: bool
    languages: list[str]


class ErrorMessage(BaseModel):
    detail: str


class Checklist(BaseModel):
    requirement_set_id: str
    destination: str
    profile: Profile
    language: Language
    items: list[ChecklistItem]
    rules: list[RuleSummary]
    translation: Translation


def _citation(row: models.Requirement | models.Rule, source: models.Source) -> Citation:
    return Citation(
        source_id=source.id,
        title=source.title,
        publisher=source.publisher,
        url=source.url,
        section=row.section,
        passage=row.passage,
        basis=row.basis,
    )


def _in_scope(model: type[models.Requirement] | type[models.Rule], destination: str):
    return or_(model.destination.is_(None), model.destination == destination)


@router.get(
    "/checklist",
    response_model=Checklist,
    responses={
        404: {"model": ErrorMessage, "description": "Unknown destination; lists available ones."},
        503: {"model": ErrorMessage, "description": "No requirement set loaded; run the seed."},
    },
)
def get_checklist(
    session: Annotated[Session, Depends(get_session)],
    destination: Annotated[str, Query(pattern=r"^[A-Z]{2}$", examples=["NL"])],
    profile: Profile,
    lang: Language = "tr",
) -> Checklist:
    """Checklist items and rules of the active requirement set for one destination and profile."""
    set_id = session.scalar(select(models.RequirementSet.id).where(models.RequirementSet.active))
    if set_id is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "No active requirement set; run `python -m app.requirements.seed`.",
        )

    destinations = set(
        session.scalars(
            select(models.Requirement.destination)
            .where(
                models.Requirement.requirement_set_id == set_id,
                models.Requirement.destination.is_not(None),
            )
            .distinct()
        )
    )
    if destination not in destinations:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"Unknown destination {destination}; available: {', '.join(sorted(destinations))}.",
        )

    requirement_rows = session.execute(
        select(models.Requirement, models.DocumentType, models.Source)
        .join(
            models.DocumentType,
            (models.DocumentType.requirement_set_id == models.Requirement.requirement_set_id)
            & (models.DocumentType.id == models.Requirement.document_type_id),
        )
        .join(models.Source, models.Source.id == models.Requirement.source_id)
        .where(
            models.Requirement.requirement_set_id == set_id,
            _in_scope(models.Requirement, destination),
            any_(models.Requirement.profiles) == profile,
        )
        .order_by(models.Requirement.position)
    ).all()

    rule_rows = session.execute(
        select(models.Rule, models.Source)
        .join(models.Source, models.Source.id == models.Rule.source_id)
        .where(
            models.Rule.requirement_set_id == set_id,
            _in_scope(models.Rule, destination),
            any_(models.Rule.profiles) == profile,
        )
        .order_by(models.Rule.position)
    ).all()

    items = [
        ChecklistItem(
            id=requirement.id,
            layer=requirement.layer,
            document=DocumentRef(
                id=document.id,
                title=document.title_tr if lang == "tr" else document.title_en,
                multiple=document.multiple,
            ),
            submit_as=requirement.submit_as,
            note=requirement.note_tr if lang == "tr" else requirement.note_en,
            source=_citation(requirement, source),
        )
        for requirement, document, source in requirement_rows
    ]
    rules = [
        RuleSummary(
            id=rule.id,
            title=rule.title_tr if lang == "tr" else rule.title_en,
            severity=rule.severity,
            kind=rule.check["kind"],
            source=_citation(rule, source),
        )
        for rule, source in rule_rows
    ]
    translation_languages = [
        language
        for rule, _ in rule_rows
        if rule.check["kind"] == "translation_present"
        for language in rule.check["languages"]
    ]
    return Checklist(
        requirement_set_id=set_id,
        destination=destination,
        profile=profile,
        language=lang,
        items=items,
        rules=rules,
        translation=Translation(
            required=bool(translation_languages), languages=translation_languages
        ),
    )

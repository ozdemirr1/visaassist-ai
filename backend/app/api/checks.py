"""Field entry and the check of an application file (FR-08, FR-09, FR-10).

The check is computed on request from the entered values with the rules of the file's own
requirement set; results are not stored in this version.
"""

import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, TypeAdapter
from sqlalchemy import any_, or_, select
from sqlalchemy.orm import Session

from app import models
from app.api.auth import ErrorMessage, current_user, require_csrf_header
from app.api.documents import KeysDep, own_application, own_document
from app.db import get_session
from app.requirements import schema
from app.rules import engine
from app.rules.values import normalise
from app.storage import documents as docs
from app.storage import field_values

router = APIRouter(tags=["checks"])
protected = [Depends(require_csrf_header)]

SessionDep = Annotated[Session, Depends(get_session)]
UserDep = Annotated[models.User, Depends(current_user)]
Language = Literal["tr", "en"]

_CHECK = TypeAdapter(schema.Check)


def _rules(session: Session, application: models.ApplicationFile) -> list[models.Rule]:
    """The rules of the file's requirement set for its destination and profile."""
    return list(
        session.scalars(
            select(models.Rule)
            .where(
                models.Rule.requirement_set_id == application.requirement_set_id,
                or_(
                    models.Rule.destination.is_(None),
                    models.Rule.destination == application.destination,
                ),
                any_(models.Rule.profiles) == application.profile,
            )
            .order_by(models.Rule.position)
        )
    )


def _asks_language(rules: list[models.Rule], document_type_id: str) -> bool:
    """Whether a translation rule of this file covers the document type."""
    return any(
        rule.check["kind"] == "translation_present"
        and document_type_id not in rule.check.get("exempt", [])
        for rule in rules
    )


def _field_definitions(
    session: Session, application: models.ApplicationFile, document: models.Document
) -> list[models.DocumentField]:
    """The fields to enter for a document; the language fields only where a rule reads them."""
    definitions = session.scalars(
        select(models.DocumentField)
        .where(
            models.DocumentField.requirement_set_id == application.requirement_set_id,
            models.DocumentField.document_type_id == document.document_type_id,
        )
        .order_by(models.DocumentField.position)
    ).all()
    if _asks_language(_rules(session, application), document.document_type_id):
        return list(definitions)
    return [d for d in definitions if not d.common]


# Field entry


class FieldOut(BaseModel):
    id: str
    type: schema.FieldType
    title: str
    optional: bool
    value: Any | None


class DocumentFields(BaseModel):
    document_id: uuid.UUID
    document_type_id: str
    fields: list[FieldOut]


class FieldValues(BaseModel):
    """Values by field ID, in the form of the field's type; null removes a value."""

    values: dict[str, Any | None]


def _fields_out(
    session: Session,
    keys: docs.Keys,
    application: models.ApplicationFile,
    document: models.Document,
    lang: Language,
) -> DocumentFields:
    values = field_values.read(session, keys, document)
    return DocumentFields(
        document_id=document.id,
        document_type_id=document.document_type_id,
        fields=[
            FieldOut(
                id=d.id,
                type=d.type,
                title=d.title_tr if lang == "tr" else d.title_en,
                optional=d.optional,
                value=values.get(d.id),
            )
            for d in _field_definitions(session, application, document)
        ],
    )


def _application_of(session: Session, document: models.Document) -> models.ApplicationFile:
    return session.get_one(models.ApplicationFile, document.application_file_id)


@router.get(
    "/documents/{document_id}/fields",
    response_model=DocumentFields,
    responses={404: {"model": ErrorMessage}},
)
def get_fields(
    document_id: uuid.UUID, session: SessionDep, user: UserDep, keys: KeysDep, lang: Language = "tr"
) -> DocumentFields:
    """The fields the applicant enters for this document, with the values entered so far."""
    document = own_document(session, user, document_id)
    return _fields_out(session, keys, _application_of(session, document), document, lang)


@router.put(
    "/documents/{document_id}/fields",
    response_model=DocumentFields,
    dependencies=protected,
    responses={
        404: {"model": ErrorMessage},
        422: {"model": ErrorMessage, "description": "Unknown field or a value of the wrong form."},
    },
)
def put_fields(
    document_id: uuid.UUID,
    body: FieldValues,
    session: SessionDep,
    user: UserDep,
    keys: KeysDep,
    lang: Language = "tr",
) -> DocumentFields:
    """Enter or change values; fields not named keep their value, null removes one."""
    document = own_document(session, user, document_id)
    application = _application_of(session, document)
    types = {d.id: d.type for d in _field_definitions(session, application, document)}
    stored: dict[str, Any | None] = {}
    for field_id, raw in body.values.items():
        if field_id not in types:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                f"{field_id}: not a field of {document.document_type_id}.",
            )
        if raw is None:
            stored[field_id] = None
            continue
        try:
            stored[field_id] = normalise(types[field_id], raw)
        except ValueError as error:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, f"{field_id}: {error}."
            ) from error
    field_values.write(session, keys, document, stored)
    session.commit()
    return _fields_out(session, keys, application, document, lang)


# Check


class IssueOut(BaseModel):
    code: str
    document_id: str | None
    document_type: str | None
    document_title: str | None
    field: str | None
    field_title: str | None
    value: Any | None
    expected: Any | None


class RuleResult(BaseModel):
    rule_id: str
    severity: Literal["error", "warning"]
    status: engine.Status
    issues: list[IssueOut]


class Summary(BaseModel):
    missing_documents: int
    passed: int
    failed: int
    incomplete: int
    skipped: int


class CheckResult(BaseModel):
    requirement_set_id: str
    missing_documents: list[str]
    rules: list[RuleResult]
    summary: Summary


def _titles(
    session: Session, set_id: str, lang: Language
) -> tuple[dict[str, str], dict[tuple[str | None, str | None], str]]:
    """Titles of the set's document types and fields, so an issue can be shown without lookups."""
    documents = {
        row.id: row.title_tr if lang == "tr" else row.title_en
        for row in session.scalars(
            select(models.DocumentType).where(models.DocumentType.requirement_set_id == set_id)
        )
    }
    fields = {
        (row.document_type_id, row.id): row.title_tr if lang == "tr" else row.title_en
        for row in session.scalars(
            select(models.DocumentField).where(models.DocumentField.requirement_set_id == set_id)
        )
    }
    return documents, fields


@router.get(
    "/applications/{file_id}/check",
    response_model=CheckResult,
    responses={404: {"model": ErrorMessage}},
)
def check_application(
    file_id: uuid.UUID, session: SessionDep, user: UserDep, keys: KeysDep, lang: Language = "tr"
) -> CheckResult:
    """Missing documents and the result of every rule on the values entered so far.

    A preliminary check of the file's preparation; it says nothing about the visa decision.
    """
    application = own_application(session, user, file_id)
    rules = _rules(session, application)
    required = dict(
        session.execute(
            select(models.Requirement.id, models.Requirement.document_type_id)
            .where(
                models.Requirement.requirement_set_id == application.requirement_set_id,
                or_(
                    models.Requirement.destination.is_(None),
                    models.Requirement.destination == application.destination,
                ),
                any_(models.Requirement.profiles) == application.profile,
            )
            .order_by(models.Requirement.position)
        ).all()
    )
    documents = [
        engine.Document(
            id=str(document.id),
            type=document.document_type_id,
            values=field_values.read(session, keys, document),
        )
        for document in docs.documents_of(session, application)
    ]
    trip = engine.Trip(
        start=application.trip_start,
        end=application.trip_end,
        application_date=application.application_date,
    )
    results = engine.evaluate(
        [engine.LoadedRule(rule.id, _CHECK.validate_python(rule.check)) for rule in rules],
        documents,
        trip,
    )
    severity = {rule.id: rule.severity for rule in rules}
    document_titles, field_titles = _titles(session, application.requirement_set_id, lang)
    missing = engine.missing_documents(required, documents)
    return CheckResult(
        requirement_set_id=application.requirement_set_id,
        missing_documents=missing,
        rules=[
            RuleResult(
                rule_id=result.rule_id,
                severity=severity[result.rule_id],
                status=result.status,
                issues=[
                    IssueOut(
                        code=issue.code,
                        document_id=issue.document_id,
                        document_type=issue.document_type,
                        document_title=document_titles.get(issue.document_type or ""),
                        field=issue.field,
                        field_title=field_titles.get((issue.document_type, issue.field)),
                        value=issue.value,
                        expected=issue.expected,
                    )
                    for issue in result.issues
                ],
            )
            for result in results
        ],
        summary=Summary(
            missing_documents=len(missing),
            **{
                state: sum(1 for r in results if r.status == state)
                for state in ("passed", "failed", "incomplete", "skipped")
            },
        ),
    )

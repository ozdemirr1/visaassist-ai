"""Field values of a document (FR-08), encrypted like the file itself (ADR 0005).

Each value is stored as JSON in the form its field type defines (`app/rules/values.py`),
encrypted with the document's data key and bound to the document and the field, so a value
cannot be moved to another field or document. The language of a document and of its translation
are not personal data and stay in plain columns of `documents`.

Functions flush but never commit.
"""

import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.rules.values import Value
from app.storage import crypto
from app.storage import documents as docs

PLAIN_FIELDS = ("language", "translation_language")


def _purpose(field_id: str) -> str:
    return f"field:{field_id}"


def _rows(session: Session, document: models.Document) -> list[models.DocumentFieldValue]:
    return list(
        session.scalars(
            select(models.DocumentFieldValue).where(
                models.DocumentFieldValue.document_id == document.id
            )
        )
    )


def read(session: Session, keys: docs.Keys, document: models.Document) -> dict[str, Value]:
    """Every entered value of the document, by field ID."""
    key = docs.data_key(keys, document)
    values: dict[str, Value] = {
        row.field_id: json.loads(
            crypto.decrypt(key, row.value_encrypted, document.id, _purpose(row.field_id))
        )
        for row in _rows(session, document)
    }
    for field_id in PLAIN_FIELDS:
        plain = getattr(document, field_id)
        if plain is not None:
            values[field_id] = plain
    return values


def write(
    session: Session,
    keys: docs.Keys,
    document: models.Document,
    values: dict[str, Value | None],
    now: datetime | None = None,
) -> None:
    """Store the given values (already in their stored form); None removes a value."""
    now = now or docs.utcnow()
    key = docs.data_key(keys, document)
    existing = {row.field_id: row for row in _rows(session, document)}
    for field_id, value in values.items():
        if field_id in PLAIN_FIELDS:
            setattr(document, field_id, value)
            continue
        row = existing.get(field_id)
        if value is None:
            if row is not None:
                session.delete(row)
            continue
        encrypted = crypto.encrypt(key, json.dumps(value).encode(), document.id, _purpose(field_id))
        if row is None:
            session.add(
                models.DocumentFieldValue(
                    document_id=document.id,
                    field_id=field_id,
                    value_encrypted=encrypted,
                    origin="entered",
                    confirmed_at=now,
                )
            )
        else:
            row.value_encrypted = encrypted
            row.origin = "entered"
            row.confirmed_at = now
    session.flush()

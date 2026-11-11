"""Consent, upload, reading, deletion and retention of documents (FR-07, FR-11, ADR 0005).

Functions flush but never commit. Deleting returns the storage keys whose files are to be
removed; the caller removes them after the commit, so a failed commit never loses a file whose
row still exists. A file whose row is gone cannot be decrypted anyway (its key was in the row),
and `remove_orphans` cleans such files up.
"""

import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.storage import crypto, metadata
from app.storage.files import LocalStorage

CONSENT_VERSION = "consent-v1"
MAX_BYTES = 10 * 1024 * 1024  # NFR-09
RETENTION_AFTER_TRIP = timedelta(days=30)  # proposal; open question to the advisor

_SIGNATURES = (
    (b"%PDF-", "application/pdf"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
)


class DocumentError(Exception):
    """Base class: the message is safe to show to the user."""


class ConsentMissing(DocumentError):
    pass


class UnsupportedType(DocumentError):
    pass


class TooLarge(DocumentError):
    pass


class NotOnChecklist(DocumentError):
    pass


def utcnow() -> datetime:
    return datetime.now(UTC)


# Consent


def valid_consent(session: Session, user: models.User) -> models.Consent | None:
    return session.scalar(
        select(models.Consent).where(
            models.Consent.user_id == user.id,
            models.Consent.version == CONSENT_VERSION,
            models.Consent.withdrawn_at.is_(None),
        )
    )


def give_consent(session: Session, user: models.User, now: datetime | None = None) -> None:
    if valid_consent(session, user) is None:
        session.add(
            models.Consent(user_id=user.id, version=CONSENT_VERSION, given_at=now or utcnow())
        )
        session.flush()


def withdraw_consent(session: Session, user: models.User, now: datetime | None = None) -> list[str]:
    """Mark every consent withdrawn and delete all of the user's documents."""
    now = now or utcnow()
    for consent in session.scalars(
        select(models.Consent).where(
            models.Consent.user_id == user.id, models.Consent.withdrawn_at.is_(None)
        )
    ):
        consent.withdrawn_at = now
    documents = session.scalars(
        select(models.Document)
        .join(
            models.ApplicationFile,
            models.ApplicationFile.id == models.Document.application_file_id,
        )
        .where(models.ApplicationFile.user_id == user.id)
    ).all()
    return delete_documents(session, documents)


# Upload


def detect_type(data: bytes) -> str | None:
    """The type from the first bytes; the file name and the browser's claim are ignored."""
    return next((mime for signature, mime in _SIGNATURES if data.startswith(signature)), None)


def delete_after(trip_end: date) -> datetime:
    return datetime.combine(trip_end + RETENTION_AFTER_TRIP, time.min, UTC)


def checklist_requirement(
    session: Session, application: models.ApplicationFile, requirement_id: str
) -> models.Requirement:
    """The requirement, if it is on this file's checklist (its set, destination and profile)."""
    requirement = session.get(models.Requirement, (application.requirement_set_id, requirement_id))
    if (
        requirement is None
        or requirement.destination not in (None, application.destination)
        or application.profile not in requirement.profiles
    ):
        raise NotOnChecklist(f"{requirement_id} is not on this application file's checklist.")
    return requirement


@dataclass(frozen=True)
class Keys:
    master: bytes
    key_id: str


def store(
    session: Session,
    storage: LocalStorage,
    keys: Keys,
    user: models.User,
    application: models.ApplicationFile,
    requirement_id: str,
    original_name: str,
    data: bytes,
    now: datetime | None = None,
) -> models.Document:
    """Validate, encrypt and store one document."""
    if valid_consent(session, user) is None:
        raise ConsentMissing("Accept the consent text before uploading documents.")
    requirement = checklist_requirement(session, application, requirement_id)
    if len(data) > MAX_BYTES:
        raise TooLarge(f"A document can have at most {MAX_BYTES // (1024 * 1024)} MB.")
    mime_type = detect_type(data)
    if mime_type is None:
        raise UnsupportedType("Only PDF, JPEG and PNG files can be uploaded.")
    # Photos lose their location data before anything is stored or hashed.
    data = metadata.remove_location(data, mime_type)

    document_id = uuid.uuid4()
    data_key = crypto.new_key()
    document = models.Document(
        id=document_id,
        application_file_id=application.id,
        requirement_id=requirement.id,
        document_type_id=requirement.document_type_id,
        storage_key=uuid.uuid4().hex,
        wrapped_key=crypto.wrap_key(keys.master, data_key, document_id, keys.key_id),
        key_id=keys.key_id,
        original_name_encrypted=crypto.encrypt(
            data_key, original_name.encode(), document_id, "name"
        ),
        mime_type=mime_type,
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        uploaded_at=now or utcnow(),
        delete_after=delete_after(application.trip_end),
    )
    storage.write(document.storage_key, crypto.encrypt(data_key, data, document_id, "file"))
    session.add(document)
    try:
        session.flush()
    except Exception:
        storage.delete(document.storage_key)
        raise
    return document


# Reading


def _data_key(keys: Keys, document: models.Document) -> bytes:
    if document.key_id != keys.key_id:
        raise crypto.DecryptionError(f"Master key {document.key_id} is not configured.")
    return crypto.unwrap_key(keys.master, document.wrapped_key, document.id, document.key_id)


def original_name(keys: Keys, document: models.Document) -> str:
    return crypto.decrypt(
        _data_key(keys, document), document.original_name_encrypted, document.id, "name"
    ).decode()


def read(storage: LocalStorage, keys: Keys, document: models.Document) -> bytes:
    return crypto.decrypt(
        _data_key(keys, document), storage.read(document.storage_key), document.id, "file"
    )


# Deletion and retention


def delete_documents(session: Session, documents: list[models.Document]) -> list[str]:
    keys = [d.storage_key for d in documents]
    for document in documents:
        session.delete(document)
    session.flush()
    return keys


def documents_of(session: Session, application: models.ApplicationFile) -> list[models.Document]:
    return list(
        session.scalars(
            select(models.Document)
            .where(models.Document.application_file_id == application.id)
            .order_by(models.Document.uploaded_at)
        )
    )


def update_retention(session: Session, application: models.ApplicationFile) -> None:
    """After a change of the trip end, move the deletion date of the file's documents."""
    for document in documents_of(session, application):
        document.delete_after = delete_after(application.trip_end)


def expired(session: Session, now: datetime | None = None) -> list[models.Document]:
    return list(
        session.scalars(
            select(models.Document).where(models.Document.delete_after <= (now or utcnow()))
        )
    )


def remove_orphans(
    session: Session, storage: LocalStorage, min_age: timedelta = timedelta(hours=1)
) -> int:
    """Delete stored files that no row points to (left by a crash or a failed commit).

    Files younger than `min_age` are left alone: their upload may still be committing.
    """
    stored = storage.keys(older_than=min_age)
    if not stored:
        return 0
    known = set(
        session.scalars(
            select(models.Document.storage_key).where(models.Document.storage_key.in_(stored))
        )
    )
    orphans = stored - known
    for key in orphans:
        storage.delete(key)
    return len(orphans)

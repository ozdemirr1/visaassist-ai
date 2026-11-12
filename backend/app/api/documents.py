"""Consent and documents: upload, list, download, delete (FR-07, FR-11, NFR-01, ADR 0005)."""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.api.auth import ErrorMessage, current_user, require_csrf_header
from app.config import get_settings
from app.db import get_session
from app.storage import crypto
from app.storage import documents as docs
from app.storage.files import LocalStorage

router = APIRouter(tags=["documents"])
protected = [Depends(require_csrf_header)]


def get_storage() -> LocalStorage:
    return LocalStorage(get_settings().storage_dir)


def get_keys() -> docs.Keys:
    settings = get_settings()
    return docs.Keys(
        crypto.decode_master_key(settings.document_master_key), settings.document_key_id
    )


SessionDep = Annotated[Session, Depends(get_session)]
UserDep = Annotated[models.User, Depends(current_user)]
StorageDep = Annotated[LocalStorage, Depends(get_storage)]
KeysDep = Annotated[docs.Keys, Depends(get_keys)]


# Consent


class ConsentState(BaseModel):
    version: str
    given: bool


@router.get("/consent", response_model=ConsentState, tags=["consent"])
def consent_state(session: SessionDep, user: UserDep) -> ConsentState:
    return ConsentState(
        version=docs.CONSENT_VERSION, given=docs.valid_consent(session, user) is not None
    )


@router.post("/consent", response_model=ConsentState, dependencies=protected, tags=["consent"])
def give_consent(session: SessionDep, user: UserDep) -> ConsentState:
    """Accept the current consent text (shown by the client in the chosen language)."""
    docs.give_consent(session, user)
    session.commit()
    return ConsentState(version=docs.CONSENT_VERSION, given=True)


@router.delete(
    "/consent", status_code=status.HTTP_204_NO_CONTENT, dependencies=protected, tags=["consent"]
)
def withdraw_consent(session: SessionDep, user: UserDep, storage: StorageDep) -> None:
    """Withdraw consent: every document of the user is deleted with its file."""
    keys = docs.withdraw_consent(session, user)
    session.commit()
    for key in keys:
        storage.delete(key)


# Documents


class DocumentOut(BaseModel):
    id: uuid.UUID
    application_file_id: uuid.UUID
    requirement_id: str
    document_type_id: str
    original_name: str
    mime_type: str
    size_bytes: int
    uploaded_at: datetime
    delete_after: datetime


def _out(keys: docs.Keys, document: models.Document) -> DocumentOut:
    return DocumentOut(
        id=document.id,
        application_file_id=document.application_file_id,
        requirement_id=document.requirement_id,
        document_type_id=document.document_type_id,
        original_name=docs.original_name(keys, document),
        mime_type=document.mime_type,
        size_bytes=document.size_bytes,
        uploaded_at=document.uploaded_at,
        delete_after=document.delete_after,
    )


def own_application(
    session: Session, user: models.User, file_id: uuid.UUID
) -> models.ApplicationFile:
    application = session.scalar(
        select(models.ApplicationFile).where(
            models.ApplicationFile.id == file_id, models.ApplicationFile.user_id == user.id
        )
    )
    if application is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application file not found.")
    return application


def own_document(session: Session, user: models.User, document_id: uuid.UUID) -> models.Document:
    document = session.scalar(
        select(models.Document)
        .join(
            models.ApplicationFile,
            models.ApplicationFile.id == models.Document.application_file_id,
        )
        .where(models.Document.id == document_id, models.ApplicationFile.user_id == user.id)
    )
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.")
    return document


async def _read_limited(upload: UploadFile) -> bytes:
    """Read at most MAX_BYTES + 1, so an oversized upload is refused without reading it all."""
    data = await upload.read(docs.MAX_BYTES + 1)
    if len(data) > docs.MAX_BYTES:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            f"A document can have at most {docs.MAX_BYTES // (1024 * 1024)} MB.",
        )
    return data


@router.post(
    "/applications/{file_id}/documents",
    status_code=status.HTTP_201_CREATED,
    response_model=DocumentOut,
    dependencies=protected,
    responses={
        403: {"model": ErrorMessage, "description": "No consent for the current version."},
        404: {"model": ErrorMessage},
        413: {"model": ErrorMessage},
        415: {"model": ErrorMessage},
        422: {"model": ErrorMessage, "description": "Requirement not on this file's checklist."},
    },
)
async def upload_document(
    file_id: uuid.UUID,
    requirement_id: Annotated[str, Form(examples=["eu-req-bank-statement"])],
    file: Annotated[UploadFile, File(description="PDF, JPEG or PNG, at most 10 MB")],
    session: SessionDep,
    user: UserDep,
    storage: StorageDep,
    keys: KeysDep,
) -> DocumentOut:
    application = own_application(session, user, file_id)
    data = await _read_limited(file)
    try:
        document = docs.store(
            session,
            storage,
            keys,
            user,
            application,
            requirement_id,
            file.filename or "document",
            data,
        )
    except docs.ConsentMissing as error:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(error)) from error
    except docs.NotOnChecklist as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error
    except docs.UnsupportedType as error:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, str(error)) from error
    except docs.TooLarge as error:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, str(error)) from error
    try:
        session.commit()
    except Exception:
        storage.delete(document.storage_key)
        raise
    return _out(keys, document)


@router.get(
    "/applications/{file_id}/documents",
    response_model=list[DocumentOut],
    responses={404: {"model": ErrorMessage}},
)
def list_documents(
    file_id: uuid.UUID, session: SessionDep, user: UserDep, keys: KeysDep
) -> list[DocumentOut]:
    application = own_application(session, user, file_id)
    return [_out(keys, d) for d in docs.documents_of(session, application)]


@router.get(
    "/documents/{document_id}/content",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}, "image/jpeg": {}, "image/png": {}}}},
)
def download_document(
    document_id: uuid.UUID, session: SessionDep, user: UserDep, storage: StorageDep, keys: KeysDep
) -> Response:
    """The decrypted file, only for its owner."""
    document = own_document(session, user, document_id)
    try:
        data = docs.read(storage, keys, document)
    except (crypto.DecryptionError, FileNotFoundError) as error:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "Document unreadable."
        ) from error
    extension = {"application/pdf": "pdf", "image/jpeg": "jpg", "image/png": "png"}
    return Response(
        content=data,
        media_type=document.mime_type,
        headers={
            # A neutral name: the original name may contain personal data and odd characters.
            "Content-Disposition": (
                f'attachment; filename="{document.document_type_id}.'
                f'{extension[document.mime_type]}"'
            ),
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-store",
        },
    )


@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=protected,
    responses={404: {"model": ErrorMessage}},
)
def delete_document(
    document_id: uuid.UUID, session: SessionDep, user: UserDep, storage: StorageDep
) -> None:
    """Delete the document and its stored file at once (FR-11)."""
    keys = docs.delete_documents(session, [own_document(session, user, document_id)])
    session.commit()
    for key in keys:
        storage.delete(key)

"""Reading the fields of an uploaded document with a model (FR-13, ADR 0007).

The endpoint returns proposed values and stores none of them: the applicant checks them in the
field form and saves them through `PUT /documents/{id}/fields`, so the rules always run on values a
person confirmed. Every call is logged with its tokens and cost, and calls stop when the month's
cost reaches the budget (NFR-06).
"""

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models
from app.ai import extraction
from app.ai.client import ModelClient, ModelError, OpenAIClient
from app.ai.prices import cost_usd
from app.api.auth import ErrorMessage, current_user, require_csrf_header
from app.api.checks import Language, _field_definitions
from app.api.documents import KeysDep, StorageDep, own_document
from app.config import get_settings
from app.db import get_session
from app.storage import documents as docs

router = APIRouter(tags=["extraction"])
protected = [Depends(require_csrf_header)]

SessionDep = Annotated[Session, Depends(get_session)]
UserDep = Annotated[models.User, Depends(current_user)]


def get_model_client() -> ModelClient | None:
    """The configured model client, or None when no API key is set."""
    settings = get_settings()
    if not settings.openai_api_key:
        return None
    return OpenAIClient(
        settings.openai_api_key, settings.extraction_model, settings.openai_base_url
    )


ModelDep = Annotated[ModelClient | None, Depends(get_model_client)]


class ExtractedField(BaseModel):
    id: str
    type: str
    title: str
    value: Any | None
    confidence: float


class ExtractionOut(BaseModel):
    document_id: uuid.UUID
    fields: list[ExtractedField]
    invalid: list[str]
    model: str
    seconds: float
    cost_usd: float | None


class ExtractionStatus(BaseModel):
    available: bool
    model: str | None


@router.get("/extraction/status", response_model=ExtractionStatus)
def extraction_status(user: UserDep, client: ModelDep) -> ExtractionStatus:
    """Whether the field form may offer reading a document with a model."""
    if client is None:
        return ExtractionStatus(available=False, model=None)
    return ExtractionStatus(available=True, model=getattr(client, "model", None))


def month_cost(session: Session, now: datetime) -> float:
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    total = session.scalar(
        select(func.coalesce(func.sum(models.ModelCall.cost_usd), 0.0)).where(
            models.ModelCall.created_at >= start
        )
    )
    return float(total or 0.0)


@router.post(
    "/documents/{document_id}/extract",
    response_model=ExtractionOut,
    dependencies=protected,
    responses={
        404: {"model": ErrorMessage},
        429: {"model": ErrorMessage, "description": "The month's model budget is used up."},
        502: {"model": ErrorMessage, "description": "The model gave no usable answer."},
        503: {"model": ErrorMessage, "description": "No model is configured."},
    },
)
def extract_fields(
    document_id: uuid.UUID,
    session: SessionDep,
    user: UserDep,
    keys: KeysDep,
    storage: StorageDep,
    client: ModelDep,
    lang: Language = "tr",
) -> ExtractionOut:
    """Propose the document's field values read by a model; nothing is stored.

    Only for synthetic documents in the prototype (ADR 0007).
    """
    document = own_document(session, user, document_id)
    if client is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Reading documents with a model is not configured."
        )
    settings = get_settings()
    model = getattr(client, "model", settings.extraction_model)
    if cost_usd(model, 0, 0) is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, f"No known price for {model}.")
    now = datetime.now(UTC)
    if month_cost(session, now) >= settings.model_monthly_budget_usd:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS, "This month's budget for the model is used up."
        )

    application = session.get_one(models.ApplicationFile, document.application_file_id)
    definitions = _field_definitions(session, application, document)
    document_type = session.get_one(
        models.DocumentType, (application.requirement_set_id, document.document_type_id)
    )
    specs = [extraction.FieldSpec(d.id, d.type, d.title_en) for d in definitions]
    content = docs.read(storage, keys, document)

    def log(result: extraction.Extraction | None) -> None:
        session.add(
            models.ModelCall(
                user_id=user.id,
                purpose="extract",
                document_type_id=document.document_type_id,
                model=result.model if result else model,
                prompt_version=extraction.PROMPT_VERSION,
                input_tokens=result.input_tokens if result else 0,
                output_tokens=result.output_tokens if result else 0,
                cost_usd=result.cost_usd if result else 0.0,
                seconds=result.seconds if result else 0.0,
                succeeded=result is not None,
                created_at=now,
            )
        )
        session.commit()

    try:
        result = extraction.extract(
            client, document_type.title_en, specs, content, document.mime_type
        )
    except ModelError as error:
        log(None)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(error)) from error
    log(result)
    return ExtractionOut(
        document_id=document.id,
        fields=[
            ExtractedField(
                id=d.id,
                type=d.type,
                title=d.title_tr if lang == "tr" else d.title_en,
                value=result.values.get(d.id),
                confidence=result.confidence.get(d.id, 0.0),
            )
            for d in definitions
        ],
        invalid=result.invalid,
        model=result.model,
        seconds=round(result.seconds, 2),
        cost_usd=result.cost_usd,
    )

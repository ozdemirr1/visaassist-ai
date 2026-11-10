"""Application files: create, list, read, update the step, delete (FR-05, FR-06, FR-11).

Every query goes through `_own_file` or filters by the current user, so an applicant can reach
only their own files; another user's file answers 404, not 403, so its existence stays hidden
(NFR-02, ADR 0004).
"""

import uuid
from datetime import UTC, date, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.api.auth import ErrorMessage, current_user, require_csrf_header
from app.db import get_session
from app.requirements import queries

router = APIRouter(prefix="/applications", tags=["applications"])
protected = [Depends(require_csrf_header)]

Profile = Literal["employed", "student"]
Step = Literal["draft", "appointment", "documents", "submitted", "decided"]
MAX_TRIP_DAYS = 90  # Schengen short stay: at most 90 days in any 180-day period

SessionDep = Annotated[Session, Depends(get_session)]
UserDep = Annotated[models.User, Depends(current_user)]


class Trip(BaseModel):
    trip_start: date
    trip_end: date

    @model_validator(mode="after")
    def _trip_is_valid(self):
        if self.trip_end < self.trip_start:
            raise ValueError("trip_end must not be before trip_start")
        if (self.trip_end - self.trip_start).days + 1 > MAX_TRIP_DAYS:
            raise ValueError(f"a short-stay trip lasts at most {MAX_TRIP_DAYS} days")
        return self


class NewApplicationFile(Trip):
    destination: str = Field(pattern=r"^[A-Z]{2}$", examples=["NL"])
    profile: Profile
    application_date: date | None = Field(
        default=None, description="Reference date for document-age rules; default today."
    )


class ApplicationFileUpdate(BaseModel):
    step: Step | None = None
    trip_start: date | None = None
    trip_end: date | None = None
    application_date: date | None = None


class Event(BaseModel):
    step: Step
    occurred_at: datetime


class ApplicationFileOut(BaseModel):
    id: uuid.UUID
    destination: str
    visa: str
    purpose: str
    profile: Profile
    trip_start: date
    trip_end: date
    application_date: date
    step: Step
    requirement_set_id: str
    created_at: datetime
    events: list[Event]


def _own_file(session: Session, user: models.User, file_id: uuid.UUID) -> models.ApplicationFile:
    application = session.scalar(
        select(models.ApplicationFile).where(
            models.ApplicationFile.id == file_id, models.ApplicationFile.user_id == user.id
        )
    )
    if application is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application file not found.")
    return application


def _out(session: Session, application: models.ApplicationFile) -> ApplicationFileOut:
    events = session.scalars(
        select(models.ApplicationEvent)
        .where(models.ApplicationEvent.application_file_id == application.id)
        .order_by(models.ApplicationEvent.occurred_at)
    )
    return ApplicationFileOut(
        id=application.id,
        destination=application.destination,
        visa=application.visa,
        purpose=application.purpose,
        profile=application.profile,
        trip_start=application.trip_start,
        trip_end=application.trip_end,
        application_date=application.application_date,
        step=application.step,
        requirement_set_id=application.requirement_set_id,
        created_at=application.created_at,
        events=[Event(step=e.step, occurred_at=e.occurred_at) for e in events],
    )


def _record_step(session: Session, application: models.ApplicationFile, step: str) -> None:
    application.step = step
    session.add(
        models.ApplicationEvent(
            application_file_id=application.id, step=step, occurred_at=datetime.now(UTC)
        )
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ApplicationFileOut,
    dependencies=protected,
    responses={422: {"model": ErrorMessage}, 503: {"model": ErrorMessage}},
)
def create_application_file(
    body: NewApplicationFile, session: SessionDep, user: UserDep
) -> ApplicationFileOut:
    """Start an application file on the active requirement set."""
    set_id = queries.active_set_id(session)
    if set_id is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "No active requirement set.")
    available = queries.destinations(session, set_id)
    if body.destination not in available:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Unknown destination {body.destination}; available: {', '.join(sorted(available))}.",
        )
    application = models.ApplicationFile(
        user_id=user.id,
        destination=body.destination,
        profile=body.profile,
        trip_start=body.trip_start,
        trip_end=body.trip_end,
        application_date=body.application_date or date.today(),
        requirement_set_id=set_id,
    )
    session.add(application)
    session.flush()
    _record_step(session, application, "draft")
    session.commit()
    return _out(session, application)


@router.get("", response_model=list[ApplicationFileOut])
def list_application_files(session: SessionDep, user: UserDep) -> list[ApplicationFileOut]:
    """The user's own files, newest first."""
    files = session.scalars(
        select(models.ApplicationFile)
        .where(models.ApplicationFile.user_id == user.id)
        .order_by(models.ApplicationFile.created_at.desc(), models.ApplicationFile.id)
    )
    return [_out(session, f) for f in files]


@router.get(
    "/{file_id}", response_model=ApplicationFileOut, responses={404: {"model": ErrorMessage}}
)
def get_application_file(
    file_id: uuid.UUID, session: SessionDep, user: UserDep
) -> ApplicationFileOut:
    return _out(session, _own_file(session, user, file_id))


@router.patch(
    "/{file_id}",
    response_model=ApplicationFileOut,
    dependencies=protected,
    responses={404: {"model": ErrorMessage}, 422: {"model": ErrorMessage}},
)
def update_application_file(
    file_id: uuid.UUID, body: ApplicationFileUpdate, session: SessionDep, user: UserDep
) -> ApplicationFileOut:
    """Change the trip dates, the reference date or the step; a new step is recorded (FR-06)."""
    application = _own_file(session, user, file_id)
    trip_start = body.trip_start or application.trip_start
    trip_end = body.trip_end or application.trip_end
    try:
        Trip(trip_start=trip_start, trip_end=trip_end)
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error
    application.trip_start, application.trip_end = trip_start, trip_end
    if body.application_date is not None:
        application.application_date = body.application_date
    if body.step is not None and body.step != application.step:
        _record_step(session, application, body.step)
    session.commit()
    return _out(session, application)


@router.delete(
    "/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=protected,
    responses={404: {"model": ErrorMessage}},
)
def delete_application_file(file_id: uuid.UUID, session: SessionDep, user: UserDep) -> None:
    """Delete the file and its events; its documents and stored files follow with FR-11."""
    session.delete(_own_file(session, user, file_id))
    session.commit()

"""Registration, login, logout and the current user (FR-04, NFR-02, ADR 0004)."""

import math
import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import models
from app.auth import service
from app.config import get_settings
from app.db import get_session

SESSION_COOKIE = "visaassist_session"
CSRF_HEADER = "X-Requested-With"
CSRF_VALUE = "visaassist"


def require_csrf_header(request: Request) -> None:
    """State-changing requests must carry a header a cross-site form cannot set (ADR 0004)."""
    if request.headers.get(CSRF_HEADER) != CSRF_VALUE:
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"Missing header {CSRF_HEADER}.")


def current_user(
    session: Annotated[Session, Depends(get_session)],
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> models.User:
    """The logged-in user; 401 without a valid session."""
    user = service.user_for_token(session, token) if token else None
    session.commit()  # keeps last_seen_at, or the deletion of an expired session
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not logged in.")
    return user


def require_admin(user: Annotated[models.User, Depends(current_user)]) -> models.User:
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Administrators only.")
    return user


router = APIRouter(prefix="/auth", tags=["auth"])
protected = [Depends(require_csrf_header)]


class Credentials(BaseModel):
    email: str = Field(max_length=254, examples=["applicant@example.com"])
    password: str = Field(max_length=service.MAX_PASSWORD_LENGTH)


class Registration(Credentials):
    language: Literal["tr", "en"] = "tr"


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    role: Literal["applicant", "admin"]
    language: Literal["tr", "en"]


class ErrorMessage(BaseModel):
    detail: str


def _user_out(user: models.User) -> UserOut:
    return UserOut(id=user.id, email=user.email, role=user.role, language=user.language)


def _set_cookie(response: Response, new: service.NewSession) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        new.token,
        expires=new.expires_at,
        httponly=True,
        secure=get_settings().cookie_secure,
        samesite="lax",
        path="/",
    )


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=UserOut,
    dependencies=protected,
    responses={409: {"model": ErrorMessage}, 422: {"model": ErrorMessage}},
)
def register(
    body: Registration,
    response: Response,
    session: Annotated[Session, Depends(get_session)],
) -> UserOut:
    """Create an applicant account and log it in."""
    try:
        user = service.create_user(session, body.email, body.password, language=body.language)
    except service.EmailTaken as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
    except (service.InvalidEmail, service.WeakPassword) as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error
    new = service.start_session(session, user)
    session.commit()
    _set_cookie(response, new)
    return _user_out(user)


@router.post(
    "/login",
    response_model=UserOut,
    dependencies=protected,
    responses={401: {"model": ErrorMessage}, 429: {"model": ErrorMessage}},
)
def login(
    body: Credentials,
    request: Request,
    response: Response,
    session: Annotated[Session, Depends(get_session)],
) -> UserOut:
    try:
        user = service.authenticate(session, body.email, body.password, _client_ip(request))
    except service.TooManyAttempts as error:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            str(error),
            headers={"Retry-After": str(max(1, math.ceil(error.retry_after.total_seconds())))},
        ) from error
    except service.InvalidCredentials as error:
        session.commit()  # the failed attempt is counted
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(error)) from error
    new = service.start_session(session, user)
    session.commit()
    _set_cookie(response, new)
    return _user_out(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, dependencies=protected)
def logout(
    response: Response,
    session: Annotated[Session, Depends(get_session)],
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> None:
    if token:
        service.end_session(session, token)
        session.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/me", response_model=UserOut, responses={401: {"model": ErrorMessage}})
def me(user: Annotated[models.User, Depends(current_user)]) -> UserOut:
    return _user_out(user)

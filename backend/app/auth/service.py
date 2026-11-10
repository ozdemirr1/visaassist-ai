"""Accounts, passwords, sessions and login throttling (ADR 0004).

Functions take the database session and, where time matters, `now`, so tests can move the
clock. They flush but never commit: the caller owns the transaction.
"""

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app import models

SESSION_LIFETIME = timedelta(days=7)
SESSION_IDLE_TIMEOUT = timedelta(days=2)
MAX_FAILED_LOGINS = 5
FAILED_LOGIN_WINDOW = timedelta(minutes=15)
MIN_PASSWORD_LENGTH = 10
MAX_PASSWORD_LENGTH = 128

_hasher = PasswordHasher()  # Argon2id with the library's default parameters


class AuthError(Exception):
    """Base class: the message is safe to show to the user."""


class InvalidEmail(AuthError):
    pass


class WeakPassword(AuthError):
    pass


class EmailTaken(AuthError):
    pass


class InvalidCredentials(AuthError):
    pass


class TooManyAttempts(AuthError):
    def __init__(self, retry_after: timedelta) -> None:
        super().__init__("Too many failed logins; try again later.")
        self.retry_after = retry_after


def utcnow() -> datetime:
    return datetime.now(UTC)


# Passwords and e-mail


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def normalise_email(email: str) -> str:
    """Lower-case and trim; reject what cannot be an address (no verification mail in fall)."""
    email = email.strip().lower()
    local, _, domain = email.partition("@")
    if not local or "." not in domain or domain.startswith(".") or len(email) > 254:
        raise InvalidEmail("Enter a valid e-mail address.")
    if any(c.isspace() for c in email):
        raise InvalidEmail("Enter a valid e-mail address.")
    return email


def check_password_strength(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise WeakPassword(f"The password needs at least {MIN_PASSWORD_LENGTH} characters.")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise WeakPassword(f"The password can have at most {MAX_PASSWORD_LENGTH} characters.")


# Accounts


def create_user(
    session: Session, email: str, password: str, role: str = "applicant", language: str = "tr"
) -> models.User:
    email = normalise_email(email)
    check_password_strength(password)
    if session.scalar(select(models.User.id).where(models.User.email == email)) is not None:
        raise EmailTaken("An account with this e-mail address already exists.")
    user = models.User(
        email=email, password_hash=hash_password(password), role=role, language=language
    )
    session.add(user)
    session.flush()
    return user


def set_password(session: Session, user: models.User, password: str) -> None:
    """Change the password and end every session of the user."""
    check_password_strength(password)
    user.password_hash = hash_password(password)
    end_all_sessions(session, user)


def authenticate(
    session: Session, email: str, password: str, ip_address: str, now: datetime | None = None
) -> models.User:
    """Check e-mail and password, record the attempt, and refuse while throttled.

    The error does not say whether the e-mail exists.
    """
    now = now or utcnow()
    email = email.strip().lower()
    _refuse_if_throttled(session, email, ip_address, now)

    user = session.scalar(select(models.User).where(models.User.email == email))
    # Verify against a dummy hash for unknown e-mails, so both cases take similar time.
    ok = verify_password(user.password_hash if user else _DUMMY_HASH, password) and user is not None
    session.add(
        models.LoginAttempt(email=email, ip_address=ip_address, succeeded=ok, attempted_at=now)
    )
    session.flush()
    if not ok:
        raise InvalidCredentials("Wrong e-mail address or password.")
    if _hasher.check_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    return user


_DUMMY_HASH = hash_password("not-a-real-password")


def _refuse_if_throttled(session: Session, email: str, ip_address: str, now: datetime) -> None:
    since = now - FAILED_LOGIN_WINDOW
    for column, value in (
        (models.LoginAttempt.email, email),
        (models.LoginAttempt.ip_address, ip_address),
    ):
        failures = session.execute(
            select(func.count(), func.min(models.LoginAttempt.attempted_at)).where(
                column == value,
                models.LoginAttempt.succeeded.is_(False),
                models.LoginAttempt.attempted_at > since,
            )
        ).one()
        count, oldest = failures
        if count >= MAX_FAILED_LOGINS:
            raise TooManyAttempts(retry_after=oldest + FAILED_LOGIN_WINDOW - now)


# Sessions


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@dataclass(frozen=True)
class NewSession:
    token: str
    expires_at: datetime


def start_session(session: Session, user: models.User, now: datetime | None = None) -> NewSession:
    """Create a session; the plain token goes only into the cookie."""
    now = now or utcnow()
    token = secrets.token_urlsafe(32)
    expires_at = now + SESSION_LIFETIME
    session.add(
        models.AuthSession(
            token_hash=_token_hash(token),
            user_id=user.id,
            created_at=now,
            last_seen_at=now,
            expires_at=expires_at,
        )
    )
    session.flush()
    return NewSession(token, expires_at)


def user_for_token(session: Session, token: str, now: datetime | None = None) -> models.User | None:
    """The user of a valid session, or None. Expired sessions are deleted on the way."""
    now = now or utcnow()
    record = session.get(models.AuthSession, _token_hash(token))
    if record is None:
        return None
    if now >= record.expires_at or now - record.last_seen_at >= SESSION_IDLE_TIMEOUT:
        session.delete(record)
        session.flush()
        return None
    record.last_seen_at = now
    return session.get(models.User, record.user_id)


def end_session(session: Session, token: str) -> None:
    session.execute(
        delete(models.AuthSession).where(models.AuthSession.token_hash == _token_hash(token))
    )


def end_all_sessions(session: Session, user: models.User) -> None:
    session.execute(delete(models.AuthSession).where(models.AuthSession.user_id == user.id))


def delete_expired_sessions(session: Session, now: datetime | None = None) -> int:
    now = now or utcnow()
    result = session.execute(
        delete(models.AuthSession).where(
            or_(
                models.AuthSession.expires_at <= now,
                models.AuthSession.last_seen_at <= now - SESSION_IDLE_TIMEOUT,
            )
        )
    )
    return result.rowcount

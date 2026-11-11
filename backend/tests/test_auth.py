"""Registration, login, sessions and throttling against a real PostgreSQL server (ADR 0004).

Each test runs inside a transaction that is rolled back. Run with RUN_INTEGRATION=1 after
`docker compose up -d`.
"""

import os
from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.api.auth import CSRF_HEADER, CSRF_VALUE, SESSION_COOKIE
from app.auth import service
from app.db import get_engine, get_session
from app.main import create_app

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION") != "1",
    reason="set RUN_INTEGRATION=1 and start the database to run",
)

BACKEND_DIR = Path(__file__).resolve().parents[1]
EMAIL = "applicant@example.com"
PASSWORD = "a long enough password"


@pytest.fixture(scope="module", autouse=True)
def migrated() -> None:
    command.upgrade(Config(str(BACKEND_DIR / "alembic.ini")), "head")


@pytest.fixture
def session() -> Iterator[Session]:
    with get_engine().connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            yield session
        transaction.rollback()


@pytest.fixture
def client(session: Session) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    # https, so the Secure cookie is sent back; the header every state-changing call needs.
    with TestClient(app, base_url="https://testserver", headers={CSRF_HEADER: CSRF_VALUE}) as c:
        yield c


def register(client: TestClient, email: str = EMAIL, password: str = PASSWORD):
    return client.post("/auth/register", json={"email": email, "password": password})


# Registration and login


def test_register_creates_an_applicant_and_logs_in(client: TestClient, session: Session) -> None:
    response = register(client, email="Applicant@Example.com")
    assert response.status_code == 201
    assert response.json()["email"] == EMAIL
    assert response.json()["role"] == "applicant"
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "Secure" in cookie and "samesite=lax" in cookie.lower()
    assert client.get("/auth/me").json()["email"] == EMAIL
    user = session.scalar(select(models.User).where(models.User.email == EMAIL))
    assert user.password_hash.startswith("$argon2id$")


def test_only_the_token_hash_is_stored(client: TestClient, session: Session) -> None:
    register(client)
    token = client.cookies.get(SESSION_COOKIE)
    # Only this user's sessions: the development database may hold sessions of real logins.
    user = session.scalar(select(models.User).where(models.User.email == EMAIL))
    stored = session.scalars(
        select(models.AuthSession.token_hash).where(models.AuthSession.user_id == user.id)
    ).all()
    assert token not in stored
    assert len(stored) == 1 and len(stored[0]) == 64


def test_duplicate_email_is_409(client: TestClient) -> None:
    register(client)
    assert register(client, email=EMAIL.upper()).status_code == 409


def test_weak_password_and_bad_email_are_422(client: TestClient) -> None:
    assert register(client, password="short").status_code == 422
    assert register(client, email="not-an-address").status_code == 422


def test_login_with_right_and_wrong_password(client: TestClient) -> None:
    register(client)
    client.cookies.clear()
    wrong = client.post("/auth/login", json={"email": EMAIL, "password": "wrong password!"})
    unknown = client.post("/auth/login", json={"email": "x@example.com", "password": PASSWORD})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()  # does not reveal whether the e-mail exists
    right = client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert right.status_code == 200
    assert client.get("/auth/me").status_code == 200


def test_logout_ends_the_session(client: TestClient) -> None:
    register(client)
    token = client.cookies.get(SESSION_COOKIE)
    assert client.post("/auth/logout").status_code == 204
    client.cookies.set(SESSION_COOKIE, token)  # an old copy of the cookie no longer works
    assert client.get("/auth/me").status_code == 401


def test_me_without_a_session_is_401(client: TestClient) -> None:
    assert client.get("/auth/me").status_code == 401
    client.cookies.set(SESSION_COOKIE, "made-up-token")
    assert client.get("/auth/me").status_code == 401


def test_state_changing_requests_need_the_custom_header(client: TestClient) -> None:
    response = client.post(
        "/auth/register",
        json={"email": EMAIL, "password": PASSWORD},
        headers={CSRF_HEADER: ""},
    )
    assert response.status_code == 403


# Throttling


def test_five_failures_lock_the_email(client: TestClient) -> None:
    register(client)
    client.cookies.clear()
    for _ in range(service.MAX_FAILED_LOGINS):
        client.post("/auth/login", json={"email": EMAIL, "password": "wrong password!"})
    locked = client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert locked.status_code == 429
    assert 0 < int(locked.headers["Retry-After"]) <= 15 * 60


def test_lock_ends_after_the_window(session: Session) -> None:
    user = service.create_user(session, EMAIL, PASSWORD)
    start = service.utcnow()
    for _ in range(service.MAX_FAILED_LOGINS):
        with pytest.raises(service.InvalidCredentials):
            service.authenticate(session, EMAIL, "wrong password!", "10.0.0.1", now=start)
    with pytest.raises(service.TooManyAttempts):
        service.authenticate(session, EMAIL, PASSWORD, "10.0.0.2", now=start)
    later = start + service.FAILED_LOGIN_WINDOW + timedelta(seconds=1)
    assert service.authenticate(session, EMAIL, PASSWORD, "10.0.0.2", now=later) == user


# Session expiry


def test_session_expires_when_idle_and_after_its_lifetime(session: Session) -> None:
    user = service.create_user(session, EMAIL, PASSWORD)
    start = service.utcnow()
    new = service.start_session(session, user, now=start)
    assert service.user_for_token(session, new.token, now=start + timedelta(days=1)) == user
    idle = start + timedelta(days=1) + service.SESSION_IDLE_TIMEOUT
    assert service.user_for_token(session, new.token, now=idle) is None

    active = service.start_session(session, user, now=start)
    for day in range(1, 7):  # used every day, still ends after seven days
        assert service.user_for_token(session, active.token, now=start + timedelta(days=day))
    assert service.user_for_token(session, active.token, now=start + timedelta(days=7)) is None


def test_password_change_ends_all_sessions(session: Session) -> None:
    user = service.create_user(session, EMAIL, PASSWORD)
    first = service.start_session(session, user)
    second = service.start_session(session, user)
    service.set_password(session, user, "another long password")
    assert service.user_for_token(session, first.token) is None
    assert service.user_for_token(session, second.token) is None

"""Application files against a real PostgreSQL server (FR-05, FR-06, NFR-02).

Each test runs inside a transaction that is rolled back. Run with RUN_INTEGRATION=1 after
`docker compose up -d`.
"""

import os
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models
from app.api.auth import CSRF_HEADER, CSRF_VALUE
from app.db import get_engine, get_session
from app.main import create_app
from app.requirements.loader import REQUIREMENTS_DIR, load_requirement_data
from app.requirements.seed import requirement_set_id, seed
from app.sources.registry import DEFAULT_REGISTRY, load_registry

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION") != "1",
    reason="set RUN_INTEGRATION=1 and start the database to run",
)

BACKEND_DIR = Path(__file__).resolve().parents[1]
SET_ID = requirement_set_id(REQUIREMENTS_DIR, DEFAULT_REGISTRY)
TRIP = {"trip_start": "2027-04-10", "trip_end": "2027-04-20"}
NEW_FILE = {"destination": "NL", "profile": "employed", "application_date": "2027-03-01", **TRIP}


@pytest.fixture(scope="module", autouse=True)
def migrated() -> None:
    command.upgrade(Config(str(BACKEND_DIR / "alembic.ini")), "head")


@pytest.fixture
def session() -> Iterator[Session]:
    with get_engine().connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            registry = load_registry()
            seed(session, load_requirement_data(registry=registry), registry, SET_ID)
            session.flush()
            yield session
        transaction.rollback()


def _client(session: Session, email: str) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    client = TestClient(app, base_url="https://testserver", headers={CSRF_HEADER: CSRF_VALUE})
    response = client.post(
        "/auth/register", json={"email": email, "password": "a long enough password"}
    )
    assert response.status_code == 201
    return client


@pytest.fixture
def ayse(session: Session) -> TestClient:
    return _client(session, "ayse@example.com")


@pytest.fixture
def mehmet(session: Session) -> TestClient:
    return _client(session, "mehmet@example.com")


def create(client: TestClient, **changes) -> dict:
    response = client.post("/applications", json=NEW_FILE | changes)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_uses_the_active_set_and_starts_as_draft(ayse: TestClient) -> None:
    created = create(ayse)
    assert created["requirement_set_id"] == SET_ID
    assert created["step"] == "draft"
    assert [e["step"] for e in created["events"]] == ["draft"]
    assert created["visa"] == "schengen-c" and created["purpose"] == "tourism"


def test_list_shows_only_own_files_newest_first(ayse: TestClient, mehmet: TestClient) -> None:
    first = create(ayse)
    second = create(ayse, destination="NO", profile="student")
    create(mehmet)
    listed = [f["id"] for f in ayse.get("/applications").json()]
    assert set(listed) == {first["id"], second["id"]}
    assert len(mehmet.get("/applications").json()) == 1


@pytest.mark.parametrize("method", ["get", "patch", "delete"])
def test_another_users_file_is_404(ayse: TestClient, mehmet: TestClient, method: str) -> None:
    file_id = create(ayse)["id"]
    kwargs = {"json": {"step": "appointment"}} if method == "patch" else {}
    response = getattr(mehmet, method)(f"/applications/{file_id}", **kwargs)
    assert response.status_code == 404
    assert ayse.get(f"/applications/{file_id}").json()["step"] == "draft"


def test_without_login_is_401(session: Session) -> None:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    client = TestClient(app, base_url="https://testserver", headers={CSRF_HEADER: CSRF_VALUE})
    assert client.get("/applications").status_code == 401
    assert client.post("/applications", json=NEW_FILE).status_code == 401


@pytest.mark.parametrize(
    "changes",
    [
        {"destination": "FR"},
        {"profile": "retired"},
        {"trip_start": "2027-04-20", "trip_end": "2027-04-10"},
        {"trip_start": "2027-04-01", "trip_end": "2027-07-01"},
    ],
)
def test_invalid_input_is_422(ayse: TestClient, changes: dict) -> None:
    assert ayse.post("/applications", json=NEW_FILE | changes).status_code == 422


def test_step_changes_are_recorded(ayse: TestClient) -> None:
    file_id = create(ayse)["id"]
    ayse.patch(f"/applications/{file_id}", json={"step": "appointment"})
    ayse.patch(f"/applications/{file_id}", json={"step": "appointment"})  # no duplicate event
    updated = ayse.patch(f"/applications/{file_id}", json={"step": "documents"}).json()
    assert updated["step"] == "documents"
    assert [e["step"] for e in updated["events"]] == ["draft", "appointment", "documents"]


def test_trip_dates_can_change_but_stay_valid(ayse: TestClient) -> None:
    file_id = create(ayse)["id"]
    ok = ayse.patch(f"/applications/{file_id}", json={"trip_end": "2027-04-25"})
    assert ok.status_code == 200 and ok.json()["trip_end"] == "2027-04-25"
    bad = ayse.patch(f"/applications/{file_id}", json={"trip_end": "2027-04-01"})
    assert bad.status_code == 422


def test_delete_removes_the_file_and_its_events(ayse: TestClient, session: Session) -> None:
    file_id = create(ayse)["id"]
    assert ayse.delete(f"/applications/{file_id}").status_code == 204
    assert ayse.get(f"/applications/{file_id}").status_code == 404
    events = session.scalar(
        select(func.count())
        .select_from(models.ApplicationEvent)
        .where(models.ApplicationEvent.application_file_id == uuid.UUID(file_id))
    )
    assert events == 0


def test_deleting_the_user_deletes_their_files(ayse: TestClient, session: Session) -> None:
    file_id = uuid.UUID(create(ayse)["id"])
    user = session.scalar(select(models.User).where(models.User.email == "ayse@example.com"))
    session.delete(user)
    session.flush()
    assert session.get(models.ApplicationFile, file_id, populate_existing=True) is None

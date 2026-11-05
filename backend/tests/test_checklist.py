"""Migrations, the seed command and GET /checklist against a real PostgreSQL server.

Each test runs inside a transaction that is rolled back, so the development database is left
as it was. Run with RUN_INTEGRATION=1 after `docker compose up -d`.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models
from app.db import get_engine, get_session
from app.main import create_app
from app.requirements.loader import REQUIREMENTS_DIR, load_requirement_data
from app.requirements.seed import active_requirement_set_id, requirement_set_id, seed
from app.sources.registry import DEFAULT_REGISTRY, load_registry

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION") != "1",
    reason="set RUN_INTEGRATION=1 and start the database to run",
)

BACKEND_DIR = Path(__file__).resolve().parents[1]
SET_ID = requirement_set_id(REQUIREMENTS_DIR, DEFAULT_REGISTRY)


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
def seeded(session: Session) -> Session:
    registry = load_registry()
    seed(session, load_requirement_data(registry=registry), registry, SET_ID)
    session.flush()
    return session


@pytest.fixture
def client(seeded: Session) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: seeded
    with TestClient(app) as client:
        yield client


def count(session: Session, model: type[models.Base]) -> int:
    return session.scalar(
        select(func.count()).select_from(model).where(model.requirement_set_id == SET_ID)
    )


# Seed


def test_seed_loads_every_requirement_and_rule(seeded: Session) -> None:
    assert active_requirement_set_id(seeded) == SET_ID
    assert count(seeded, models.Requirement) == 17
    assert count(seeded, models.Rule) == 24
    assert count(seeded, models.DocumentType) == 13


def test_seeding_the_same_files_again_changes_nothing(seeded: Session) -> None:
    registry = load_registry()
    result = seed(seeded, load_requirement_data(registry=registry), registry, SET_ID)
    assert result.created is False
    assert count(seeded, models.Requirement) == 17


def test_a_new_set_replaces_the_active_one(seeded: Session) -> None:
    registry = load_registry()
    other = "0" * 64
    seed(seeded, load_requirement_data(registry=registry), registry, other)
    seeded.flush()
    active = seeded.scalars(
        select(models.RequirementSet.id).where(models.RequirementSet.active)
    ).all()
    assert active == [other]


# GET /checklist


@pytest.mark.parametrize(
    ("destination", "profile", "items", "rules"),
    [("NL", "employed", 12, 16), ("NL", "student", 9, 11), ("NO", "employed", 12, 15)],
)
def test_checklist_counts(
    client: TestClient, destination: str, profile: str, items: int, rules: int
) -> None:
    response = client.get("/checklist", params={"destination": destination, "profile": profile})
    assert response.status_code == 200
    body = response.json()
    assert body["requirement_set_id"] == SET_ID
    assert len(body["items"]) == items
    assert len(body["rules"]) == rules


def test_every_item_cites_an_official_source(client: TestClient) -> None:
    body = client.get("/checklist", params={"destination": "NL", "profile": "employed"}).json()
    for item in body["items"] + body["rules"]:
        source = item["source"]
        assert source["url"].startswith("https://")
        assert source["passage"]
        assert source["basis"] in {"stated", "derived"}


def test_titles_follow_the_language(client: TestClient) -> None:
    params = {"destination": "NL", "profile": "employed"}
    tr = client.get("/checklist", params=params | {"lang": "tr"}).json()
    en = client.get("/checklist", params=params | {"lang": "en"}).json()
    assert [i["id"] for i in tr["items"]] == [i["id"] for i in en["items"]]
    assert tr["items"][0]["document"]["title"] != en["items"][0]["document"]["title"]


def test_translation_is_required_only_for_norway(client: TestClient) -> None:
    norway = client.get("/checklist", params={"destination": "NO", "profile": "employed"}).json()
    netherlands = client.get(
        "/checklist", params={"destination": "NL", "profile": "employed"}
    ).json()
    assert norway["translation"] == {"required": True, "languages": ["en", "no"]}
    assert netherlands["translation"] == {"required": False, "languages": []}


def test_unknown_destination_is_404(client: TestClient) -> None:
    response = client.get("/checklist", params={"destination": "FR", "profile": "employed"})
    assert response.status_code == 404
    assert "NL" in response.json()["detail"]


def test_invalid_profile_is_422(client: TestClient) -> None:
    response = client.get("/checklist", params={"destination": "NL", "profile": "retired"})
    assert response.status_code == 422


def test_no_active_set_is_503(session: Session) -> None:
    session.execute(models.RequirementSet.__table__.update().values(active=False))
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as client:
        response = client.get("/checklist", params={"destination": "NL", "profile": "employed"})
    assert response.status_code == 503

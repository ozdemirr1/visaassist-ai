"""Consent, upload, download and deletion of documents against PostgreSQL (ADR 0005).

Files go to a temporary directory; each test's database work is rolled back. Run with
RUN_INTEGRATION=1 after `docker compose up -d`.
"""

import os
import uuid
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
from app.api.auth import CSRF_HEADER, CSRF_VALUE
from app.api.documents import get_storage
from app.db import get_engine, get_session
from app.main import create_app
from app.requirements.loader import REQUIREMENTS_DIR, load_requirement_data
from app.requirements.seed import requirement_set_id, seed
from app.sources.registry import DEFAULT_REGISTRY, load_registry
from app.storage import documents as docs
from app.storage.files import LocalStorage

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION") != "1",
    reason="set RUN_INTEGRATION=1 and start the database to run",
)

BACKEND_DIR = Path(__file__).resolve().parents[1]
SET_ID = requirement_set_id(REQUIREMENTS_DIR, DEFAULT_REGISTRY)
PDF = b"%PDF-1.7\n% synthetic test document, no personal data\n%%EOF\n"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
BANK = "eu-req-bank-statement"


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


@pytest.fixture
def storage(tmp_path: Path) -> LocalStorage:
    return LocalStorage(tmp_path / "storage")


def _client(session: Session, storage: LocalStorage, email: str) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_storage] = lambda: storage
    client = TestClient(app, base_url="https://testserver", headers={CSRF_HEADER: CSRF_VALUE})
    assert (
        client.post(
            "/auth/register", json={"email": email, "password": "a long enough password"}
        ).status_code
        == 201
    )
    return client


@pytest.fixture
def ayse(session: Session, storage: LocalStorage) -> TestClient:
    return _client(session, storage, "ayse@example.com")


@pytest.fixture
def mehmet(session: Session, storage: LocalStorage) -> TestClient:
    return _client(session, storage, "mehmet@example.com")


def new_file(client: TestClient, profile: str = "employed") -> str:
    response = client.post(
        "/applications",
        json={
            "destination": "NL",
            "profile": profile,
            "trip_start": "2027-04-10",
            "trip_end": "2027-04-20",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def upload(client: TestClient, file_id: str, data: bytes = PDF, requirement: str = BANK, name="x"):
    return client.post(
        f"/applications/{file_id}/documents",
        data={"requirement_id": requirement},
        files={"file": (name, data, "application/pdf")},
    )


@pytest.fixture
def consenting(ayse: TestClient) -> TestClient:
    assert ayse.post("/consent").json() == {"version": docs.CONSENT_VERSION, "given": True}
    return ayse


# Consent


def test_upload_without_consent_is_403(ayse: TestClient) -> None:
    assert ayse.get("/consent").json()["given"] is False
    assert upload(ayse, new_file(ayse)).status_code == 403


def test_withdrawing_consent_deletes_every_document(
    consenting: TestClient, storage: LocalStorage
) -> None:
    file_id = new_file(consenting)
    upload(consenting, file_id)
    upload(consenting, new_file(consenting))
    assert len(storage.keys()) == 2
    assert consenting.delete("/consent").status_code == 204
    assert storage.keys() == set()
    assert consenting.get(f"/applications/{file_id}/documents").json() == []
    assert upload(consenting, file_id).status_code == 403


# Upload and download


def test_upload_stores_only_ciphertext_under_a_random_name(
    consenting: TestClient, storage: LocalStorage
) -> None:
    response = upload(consenting, new_file(consenting), name="ayse_yilmaz_bank.pdf")
    assert response.status_code == 201
    body = response.json()
    assert body["original_name"] == "ayse_yilmaz_bank.pdf"
    assert body["mime_type"] == "application/pdf"
    assert body["document_type_id"] == "bank_statement"
    assert body["delete_after"].startswith("2027-05-20")
    (stored,) = storage.root.rglob("*/*")
    assert "ayse" not in stored.name
    assert PDF not in stored.read_bytes() and b"%PDF" not in stored.read_bytes()


def test_download_returns_the_original_bytes(consenting: TestClient) -> None:
    document_id = upload(consenting, new_file(consenting), data=PNG).json()["id"]
    response = consenting.get(f"/documents/{document_id}/content")
    assert response.status_code == 200
    assert response.content == PNG
    assert response.headers["content-type"] == "image/png"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "no-store"
    assert "attachment" in response.headers["content-disposition"]


def test_type_is_checked_from_content_not_name(consenting: TestClient) -> None:
    response = upload(consenting, new_file(consenting), data=b"MZ\x90\x00 program", name="a.pdf")
    assert response.status_code == 415


def test_more_than_10_mb_is_413(consenting: TestClient) -> None:
    big = PDF + b"0" * docs.MAX_BYTES
    assert upload(consenting, new_file(consenting), data=big).status_code == 413


def test_requirement_must_be_on_the_files_checklist(consenting: TestClient) -> None:
    student_file = new_file(consenting, profile="student")
    assert upload(consenting, student_file, requirement="eu-req-payslips").status_code == 422
    assert upload(consenting, student_file, requirement="no-such-item").status_code == 422
    assert upload(consenting, student_file, requirement="eu-req-yok-certificate").status_code == 201


def test_a_tampered_file_is_not_served(consenting: TestClient, storage: LocalStorage) -> None:
    document_id = upload(consenting, new_file(consenting)).json()["id"]
    (stored,) = storage.root.rglob("*/*")
    data = bytearray(stored.read_bytes())
    data[-1] ^= 1
    stored.write_bytes(bytes(data))
    assert consenting.get(f"/documents/{document_id}/content").status_code == 500


# Ownership and deletion


def test_another_user_cannot_see_download_upload_or_delete(
    consenting: TestClient, mehmet: TestClient
) -> None:
    file_id = new_file(consenting)
    document_id = upload(consenting, file_id).json()["id"]
    mehmet.post("/consent")
    assert mehmet.get(f"/applications/{file_id}/documents").status_code == 404
    assert mehmet.get(f"/documents/{document_id}/content").status_code == 404
    assert upload(mehmet, file_id).status_code == 404
    assert mehmet.delete(f"/documents/{document_id}").status_code == 404
    assert consenting.get(f"/documents/{document_id}/content").status_code == 200


def test_delete_removes_the_file_from_disk(consenting: TestClient, storage: LocalStorage) -> None:
    document_id = upload(consenting, new_file(consenting)).json()["id"]
    assert consenting.delete(f"/documents/{document_id}").status_code == 204
    assert storage.keys() == set()
    assert consenting.get(f"/documents/{document_id}/content").status_code == 404


def test_deleting_the_application_file_removes_its_documents(
    consenting: TestClient, storage: LocalStorage
) -> None:
    file_id = new_file(consenting)
    upload(consenting, file_id)
    upload(consenting, file_id, data=PNG)
    assert consenting.delete(f"/applications/{file_id}").status_code == 204
    assert storage.keys() == set()


def test_changing_the_trip_end_moves_the_deletion_date(consenting: TestClient) -> None:
    file_id = new_file(consenting)
    upload(consenting, file_id)
    consenting.patch(f"/applications/{file_id}", json={"trip_end": "2027-04-25"})
    (document,) = consenting.get(f"/applications/{file_id}/documents").json()
    assert document["delete_after"].startswith("2027-05-25")


# Retention and orphans


def test_expired_documents_and_orphans_are_cleaned_up(
    consenting: TestClient, session: Session, storage: LocalStorage
) -> None:
    file_id = new_file(consenting)
    upload(consenting, file_id)
    document = session.scalar(
        select(models.Document).where(models.Document.application_file_id == uuid.UUID(file_id))
    )
    keys = docs.delete_documents(
        session, docs.expired(session, now=document.delete_after + timedelta(seconds=1))
    )
    assert document.storage_key in keys
    orphan = uuid.uuid4().hex
    storage.write(orphan, b"left by a crash")
    assert docs.remove_orphans(session, storage, min_age=timedelta(0)) == 2  # orphan + expired
    assert storage.keys() == set()

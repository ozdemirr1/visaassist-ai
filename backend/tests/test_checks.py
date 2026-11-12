"""Field entry and the check of an application file against PostgreSQL (FR-08 to FR-10).

Files go to a temporary directory; each test's database work is rolled back. Run with
RUN_INTEGRATION=1 after `docker compose up -d`. The documents and values are invented.
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
from app.api.auth import CSRF_HEADER, CSRF_VALUE
from app.api.documents import get_storage
from app.db import get_engine, get_session
from app.main import create_app
from app.requirements.loader import REQUIREMENTS_DIR, load_requirement_data
from app.requirements.seed import requirement_set_id, seed
from app.sources.registry import DEFAULT_REGISTRY, load_registry
from app.storage.files import LocalStorage

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION") != "1",
    reason="set RUN_INTEGRATION=1 and start the database to run",
)

BACKEND_DIR = Path(__file__).resolve().parents[1]
SET_ID = requirement_set_id(REQUIREMENTS_DIR, DEFAULT_REGISTRY)
PDF = b"%PDF-1.7\n% synthetic test document, no personal data\n%%EOF\n"
BANK = "eu-req-bank-statement"
BANK_RULE = "eu-rule-bank-statement-period"
GOOD_PERIOD = {"period_start": "2026-11-25", "period_end": "2027-02-25"}


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


def _client(session: Session, storage: LocalStorage, email: str) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_storage] = lambda: storage
    client = TestClient(app, base_url="https://testserver", headers={CSRF_HEADER: CSRF_VALUE})
    registered = client.post(
        "/auth/register", json={"email": email, "password": "a long enough password"}
    )
    assert registered.status_code == 201
    assert client.post("/consent").status_code == 200
    return client


@pytest.fixture
def storage(tmp_path: Path) -> LocalStorage:
    return LocalStorage(tmp_path / "storage")


@pytest.fixture
def ayse(session: Session, storage: LocalStorage) -> TestClient:
    return _client(session, storage, "ayse@example.com")


@pytest.fixture
def mehmet(session: Session, storage: LocalStorage) -> TestClient:
    return _client(session, storage, "mehmet@example.com")


def new_file(client: TestClient, destination: str = "NL") -> str:
    response = client.post(
        "/applications",
        json={
            "destination": destination,
            "profile": "employed",
            "trip_start": "2027-04-10",
            "trip_end": "2027-04-20",
            "application_date": "2027-03-01",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def upload(client: TestClient, file_id: str, requirement: str = BANK) -> str:
    response = client.post(
        f"/applications/{file_id}/documents",
        data={"requirement_id": requirement},
        files={"file": ("x.pdf", PDF, "application/pdf")},
    )
    assert response.status_code == 201
    return response.json()["id"]


def put(client: TestClient, document_id: str, values: dict):
    return client.put(f"/documents/{document_id}/fields", json={"values": values})


def rule(client: TestClient, file_id: str, rule_id: str) -> dict:
    check = client.get(f"/applications/{file_id}/check").json()
    return next(r for r in check["rules"] if r["rule_id"] == rule_id)


# Field entry


def test_fields_of_a_document_are_listed_in_the_interface_language(ayse: TestClient) -> None:
    document_id = upload(ayse, new_file(ayse))
    body = ayse.get(f"/documents/{document_id}/fields").json()
    assert body["document_type_id"] == "bank_statement"
    assert [f["id"] for f in body["fields"]] == [
        "holder_name",
        "period_start",
        "period_end",
        "issue_date",
    ]
    assert body["fields"][0] == {
        "id": "holder_name",
        "type": "text",
        "title": "Hesap sahibi",
        "optional": False,
        "value": None,
    }
    english = ayse.get(f"/documents/{document_id}/fields", params={"lang": "en"}).json()
    assert english["fields"][0]["title"] == "Account holder"


def test_entered_values_come_back_and_are_stored_encrypted(
    ayse: TestClient, session: Session
) -> None:
    document_id = upload(ayse, new_file(ayse))
    response = put(ayse, document_id, {"holder_name": "  Ayşe   Yılmaz ", **GOOD_PERIOD})
    assert response.status_code == 200
    values = {f["id"]: f["value"] for f in response.json()["fields"]}
    assert values == {"holder_name": "Ayşe Yılmaz", **GOOD_PERIOD, "issue_date": None}
    assert ayse.get(f"/documents/{document_id}/fields").json() == response.json()

    rows = session.scalars(select(models.DocumentFieldValue)).all()
    assert {row.field_id for row in rows} == {"holder_name", "period_start", "period_end"}
    for row in rows:
        assert b"Y\xc4\xb1lmaz" not in row.value_encrypted and b"2027" not in row.value_encrypted
        assert row.origin == "entered" and row.confirmed_at is not None


def test_null_removes_a_value_and_other_fields_keep_theirs(ayse: TestClient) -> None:
    document_id = upload(ayse, new_file(ayse))
    put(ayse, document_id, {"holder_name": "Ayşe Yılmaz", **GOOD_PERIOD})
    body = put(ayse, document_id, {"holder_name": None, "period_end": "2027-02-20"}).json()
    values = {f["id"]: f["value"] for f in body["fields"]}
    assert values == {
        "holder_name": None,
        "period_start": "2026-11-25",
        "period_end": "2027-02-20",
        "issue_date": None,
    }


@pytest.mark.parametrize(
    "values",
    [
        {"period_start": "25.11.2026"},
        {"period_start": 20261125},
        {"holder_name": ""},
        {"holder_name": "x" * 201},
        {"iban": "TR00"},
        {"language": "tr"},  # no translation rule for the Netherlands: not asked, not accepted
    ],
)
def test_a_wrong_value_or_an_unknown_field_is_422_and_nothing_is_stored(
    ayse: TestClient, session: Session, values: dict
) -> None:
    document_id = upload(ayse, new_file(ayse))
    response = put(ayse, document_id, {"issue_date": "2027-02-25", **values})
    assert response.status_code == 422
    assert next(iter(values)) in response.json()["detail"]
    assert session.scalar(select(func.count()).select_from(models.DocumentFieldValue)) == 0


def test_money_int_and_bool_fields_keep_their_form(ayse: TestClient) -> None:
    file_id = new_file(ayse)
    insurance = upload(ayse, file_id, "nl-req-travel-insurance")
    body = put(
        ayse,
        insurance,
        {"coverage_amount": {"amount": 30000, "currency": "EUR"}, "covers_all_schengen": True},
    ).json()
    values = {f["id"]: f["value"] for f in body["fields"]}
    assert values["coverage_amount"] == {"amount": 30000.0, "currency": "EUR"}
    assert values["covers_all_schengen"] is True
    assert put(ayse, insurance, {"coverage_amount": {"amount": 30000}}).status_code == 422
    assert put(ayse, insurance, {"covers_all_schengen": "yes"}).status_code == 422

    passport = upload(ayse, file_id, "nl-req-passport")
    assert put(ayse, passport, {"blank_pages": 4}).status_code == 200
    assert put(ayse, passport, {"blank_pages": True}).status_code == 422
    assert put(ayse, passport, {"blank_pages": 2.5}).status_code == 422


def test_language_is_asked_only_where_a_translation_rule_reads_it(ayse: TestClient) -> None:
    file_id = new_file(ayse, destination="NO")
    bank = upload(ayse, file_id)
    ids = [f["id"] for f in ayse.get(f"/documents/{bank}/fields").json()["fields"]]
    assert ids[-2:] == ["language", "translation_language"]
    body = put(ayse, bank, {"language": "tr", "translation_language": "en"}).json()
    assert {f["id"]: f["value"] for f in body["fields"]}["translation_language"] == "en"
    assert put(ayse, bank, {"language": "Turkish"}).status_code == 422

    passport = upload(ayse, file_id, "no-req-passport")
    ids = [f["id"] for f in ayse.get(f"/documents/{passport}/fields").json()["fields"]]
    assert "language" not in ids


def test_another_user_cannot_read_or_enter_fields_or_run_the_check(
    ayse: TestClient, mehmet: TestClient
) -> None:
    file_id = new_file(ayse)
    document_id = upload(ayse, file_id)
    assert mehmet.get(f"/documents/{document_id}/fields").status_code == 404
    assert put(mehmet, document_id, {"holder_name": "Mehmet"}).status_code == 404
    assert mehmet.get(f"/applications/{file_id}/check").status_code == 404


def test_deleting_a_document_deletes_its_values(ayse: TestClient, session: Session) -> None:
    document_id = upload(ayse, new_file(ayse))
    put(ayse, document_id, GOOD_PERIOD)
    assert ayse.delete(f"/documents/{document_id}").status_code == 204
    session.expire_all()
    assert session.scalar(select(func.count()).select_from(models.DocumentFieldValue)) == 0


# Check


def test_an_empty_file_misses_every_document_and_no_rule_has_run(ayse: TestClient) -> None:
    check = ayse.get(f"/applications/{new_file(ayse)}/check").json()
    assert check["requirement_set_id"] == SET_ID
    assert len(check["missing_documents"]) == 12 and BANK in check["missing_documents"]
    assert len(check["rules"]) == 16
    assert check["summary"] == {
        "missing_documents": 12,
        "passed": 0,
        "failed": 0,
        "incomplete": 0,
        "skipped": 16,
    }


def test_a_rule_follows_the_entered_values(ayse: TestClient) -> None:
    file_id = new_file(ayse)
    document_id = upload(ayse, file_id)
    check = ayse.get(f"/applications/{file_id}/check").json()
    assert BANK not in check["missing_documents"] and len(check["missing_documents"]) == 11

    result = rule(ayse, file_id, BANK_RULE)
    assert result["status"] == "incomplete" and result["severity"] == "error"
    assert result["issues"][0]["code"] == "value_missing"

    put(ayse, document_id, {"period_start": "2026-12-20", "period_end": "2027-02-25"})
    result = rule(ayse, file_id, BANK_RULE)
    assert result["status"] == "failed"
    assert result["issues"] == [
        {
            "code": "period_too_short",
            "document_id": document_id,
            "document_type": "bank_statement",
            "document_title": "Banka hesap dökümü",
            "field": "period_start",
            "field_title": "Döküm başlangıcı",
            "value": "2026-12-20",
            "expected": "2026-11-25",
        }
    ]

    put(ayse, document_id, GOOD_PERIOD)
    assert rule(ayse, file_id, BANK_RULE) == {
        "rule_id": BANK_RULE,
        "severity": "error",
        "status": "passed",
        "issues": [],
    }


def test_names_are_compared_with_the_passport(ayse: TestClient) -> None:
    file_id = new_file(ayse)
    passport = upload(ayse, file_id, "nl-req-passport")
    bank = upload(ayse, file_id)
    put(ayse, passport, {"full_name": "Ayşe Yılmaz"})
    put(ayse, bank, {"holder_name": "YILMAZ AYSE"})
    assert rule(ayse, file_id, "eu-rule-names-match")["status"] == "passed"
    put(ayse, bank, {"holder_name": "Ayşe Kaya"})
    result = rule(ayse, file_id, "eu-rule-names-match")
    assert result["status"] == "failed"
    assert result["issues"][0]["expected"] == "Ayşe Yılmaz"

"""Loading the demo files into the application (`app.demo.load`).

The first tests need no database. The others load the demo into PostgreSQL, run the same check
the findings page uses, and roll back; run them with RUN_INTEGRATION=1 after
`docker compose up -d`.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models
from app.api.checks import _check
from app.api.documents import get_keys
from app.auth import service
from app.db import get_engine
from app.demo.files import Change, SetValue, changed, findings, load_all
from app.demo.load import DemoLoadError, is_reserved, load
from app.demo.pdf import sample_pdf
from app.requirements.loader import REQUIREMENTS_DIR, load_requirement_data
from app.requirements.seed import requirement_set_id, seed
from app.sources.registry import DEFAULT_REGISTRY, load_registry
from app.storage import documents as docs
from app.storage.files import LocalStorage

BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA = load_requirement_data()
DEMOS = {d.id: d for d in load_all()}
integration = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION") != "1",
    reason="set RUN_INTEGRATION=1 and start the database to run",
)


# Without a database


def test_the_sample_pdf_is_a_pdf_the_upload_accepts() -> None:
    pdf = sample_pdf("SAMPLE - Passport", ["full_name: Deniz Örnek (Ş, ğ, ı)"])
    assert docs.detect_type(pdf) == "application/pdf"
    assert pdf.rstrip().endswith(b"%%EOF")
    assert b"(SAMPLE) Tj" in pdf and b"Deniz \xd6rnek \\(S, g, i\\)" in pdf


def test_only_reserved_example_addresses_are_used() -> None:
    assert is_reserved("demo@visaassist.example")
    assert is_reserved("someone@example.org")
    assert not is_reserved("furkan@gmail.com")
    assert not is_reserved("demo@example.com.tr")


def test_several_errors_can_be_applied_to_one_file() -> None:
    demo = DEMOS["employed-nl"]
    errors = {e.id: e for e in demo.errors}
    chosen = [errors["E01"].change, errors["E06"].change]
    documents = changed(demo, chosen)
    assert len(documents) == len(demo.documents) - 1
    found = findings(demo, DATA, chosen)
    assert "nl-req-travel-insurance" in found.missing
    assert "eu-rule-names-match" in found.failed


def test_changes_do_not_alter_the_demo_file() -> None:
    demo = DEMOS["student-no"]
    before = demo.model_dump()
    changed(demo, [Change(set=SetValue(document="passport", field="blank_pages", value=1))])
    assert demo.model_dump() == before


# With the database


@pytest.fixture
def session() -> Iterator[Session]:
    command.upgrade(Config(str(BACKEND_DIR / "alembic.ini")), "head")
    with get_engine().connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            registry = load_registry()
            seed(
                session,
                load_requirement_data(registry=registry),
                registry,
                requirement_set_id(REQUIREMENTS_DIR, DEFAULT_REGISTRY),
            )
            session.flush()
            yield session
        transaction.rollback()


@pytest.fixture
def storage(tmp_path: Path) -> LocalStorage:
    return LocalStorage(tmp_path / "storage")


EMAIL = "demo-test@visaassist.example"


def _files(session: Session, email: str) -> list[models.ApplicationFile]:
    user = session.scalar(select(models.User).where(models.User.email == email))
    return list(
        session.scalars(
            select(models.ApplicationFile)
            .where(models.ApplicationFile.user_id == user.id)
            .order_by(models.ApplicationFile.destination)
        )
    )


@integration
def test_the_loaded_clean_files_give_no_finding(session, storage) -> None:
    loaded, removed = load(session, storage, get_keys(), EMAIL, "a long demo password")
    assert removed == [] and loaded.new_password is None
    files = _files(session, EMAIL)
    assert [(f.destination, f.profile) for f in files] == [("NL", "employed"), ("NO", "student")]
    for application in files:
        result = _check(session, get_keys(), application, "en")
        assert result.missing_documents == []
        assert result.summary.failed == 0 and result.summary.incomplete == 0
        for document in docs.documents_of(session, application):
            assert docs.read(storage, get_keys(), document).startswith(b"%PDF-")


@integration
def test_an_applied_error_shows_on_the_check(session, storage) -> None:
    load(session, storage, get_keys(), EMAIL, "a long demo password", ["E06", "S04"])
    by_destination = {f.destination: f for f in _files(session, EMAIL)}
    nl = _check(session, get_keys(), by_destination["NL"], "en")
    assert [r.rule_id for r in nl.rules if r.status == "failed"] == ["eu-rule-names-match"]
    no = _check(session, get_keys(), by_destination["NO"], "en")
    assert no.missing_documents == ["eu-req-accommodation"]


@integration
def test_loading_again_replaces_the_files_and_keeps_the_password(session, storage) -> None:
    first, _ = load(session, storage, get_keys(), EMAIL)
    assert first.new_password is not None
    _, removed = load(session, storage, get_keys(), EMAIL)
    assert len(removed) == sum(len(d.documents) for d in DEMOS.values())
    assert len(_files(session, EMAIL)) == 2
    user = session.scalar(select(models.User).where(models.User.email == EMAIL))
    stored = session.scalar(
        select(func.count())
        .select_from(models.Document)
        .join(models.ApplicationFile)
        .where(models.ApplicationFile.user_id == user.id)
    )
    assert stored == sum(len(d.documents) for d in DEMOS.values())
    assert service.verify_password(user.password_hash, first.new_password)


@integration
def test_a_real_looking_address_or_an_unknown_error_is_refused(session, storage) -> None:
    with pytest.raises(DemoLoadError, match="reserved"):
        load(session, storage, get_keys(), "someone@gmail.com")
    with pytest.raises(DemoLoadError, match="X99"):
        load(session, storage, get_keys(), EMAIL, error_ids=["X99"])

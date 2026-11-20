"""Load the demo files into the application: an account with one application file per demo file.

    uv run python -m app.demo.load                        # both files, without errors
    uv run python -m app.demo.load --error E06 --error S03
    uv run python -m app.demo.load --list-errors

Every document gets its rendered image marked SAMPLE (`data/demo/documents/`, made by
`app.demo.render`), or a one-page SAMPLE PDF where there is none, and the field values of the demo
file, entered as an applicant would enter them; `--error` applies labelled errors first, so the
findings page has something to show. Run the seed command before this one.

The account is reserved for the demo: each run deletes its application files and documents and
creates them again, which is why only addresses under a reserved example domain are accepted.
The password is taken from DEMO_PASSWORD; without it a new account gets a random password,
printed once, and an existing account keeps its password.
"""

import argparse
import os
import secrets
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.api.documents import get_keys, get_storage
from app.auth import service
from app.db import get_engine
from app.demo.files import DEMO_DIR, DemoFile, changed, load_all, stored_values
from app.demo.pdf import sample_pdf
from app.requirements import queries
from app.requirements.loader import RequirementData, load_requirement_data
from app.storage import documents as docs
from app.storage import field_values
from app.storage.files import LocalStorage

DEFAULT_EMAIL = "demo@visaassist.example"
IMAGE_DIR = DEMO_DIR / "documents"  # rendered by app.demo.render and tools/demo-documents
# RFC 2606 / RFC 6761: names that can never belong to a real mailbox.
RESERVED_DOMAINS = (".example", "@example.com", "@example.org", "@example.net")


class DemoLoadError(Exception):
    """The message is shown to the person running the command."""


@dataclass
class Loaded:
    email: str
    new_password: str | None
    files: list[tuple[DemoFile, list[str], int]] = field(default_factory=list)  # errors, documents


def is_reserved(email: str) -> bool:
    return email.endswith(RESERVED_DOMAINS)


def _account(session: Session, email: str, password: str | None) -> tuple[models.User, str | None]:
    """The demo account, created if needed; returns the password if a new one was generated."""
    user = session.scalar(select(models.User).where(models.User.email == email))
    if user is None:
        generated = None if password else secrets.token_urlsafe(12)
        user = service.create_user(session, email, password or generated, role="applicant")
        return user, generated
    if user.role != "applicant":
        raise DemoLoadError(f"{email} is an administrator account, not a demo account.")
    if password:
        service.set_password(session, user, password)
    return user, None


def _clear(session: Session, user: models.User) -> list[str]:
    """Delete the account's application files and documents; returns the files to remove."""
    keys: list[str] = []
    for application in session.scalars(
        select(models.ApplicationFile).where(models.ApplicationFile.user_id == user.id)
    ).all():
        keys += docs.delete_documents(session, docs.documents_of(session, application))
        session.delete(application)
    session.flush()
    return keys


def _requirement_for(data: RequirementData, demo: DemoFile) -> dict[str, str]:
    """Checklist item per document type of the demo file's destination and profile."""
    items: dict[str, str] = {}
    for requirement in data.ruleset(demo.destination).checklist(demo.profile):
        if requirement.document in items:
            raise DemoLoadError(f"{demo.id}: two checklist items ask for {requirement.document}.")
        items[requirement.document] = requirement.id
    return items


def _add_file(
    session: Session,
    storage: LocalStorage,
    keys: docs.Keys,
    data: RequirementData,
    user: models.User,
    set_id: str,
    demo: DemoFile,
    error_ids: list[str],
    now: datetime,
) -> int:
    chosen = [e for e in demo.errors if e.id in error_ids]
    application = models.ApplicationFile(
        user_id=user.id,
        destination=demo.destination,
        profile=demo.profile,
        trip_start=demo.trip.start,
        trip_end=demo.trip.end,
        application_date=demo.trip.application_date,
        requirement_set_id=set_id,
    )
    session.add(application)
    session.flush()
    for step in ("draft", "appointment", "documents"):
        session.add(
            models.ApplicationEvent(application_file_id=application.id, step=step, occurred_at=now)
        )
    application.step = "documents"

    items = _requirement_for(data, demo)
    # Which chosen error changed a value of each document; its image shows the changed value.
    changed_by: dict[str, list[str]] = {}
    for error in chosen:
        if error.change.set is not None:
            changed_by.setdefault(error.change.set.document, []).append(error.id)
    count = 0
    for document in changed(demo, [e.change for e in chosen]):
        if document.type not in items:
            raise DemoLoadError(f"{demo.id}: {document.type} is not on the checklist.")
        values = stored_values(data, document)
        errors = changed_by.get(document.id, [])
        name, content = _document_file(data, demo, document, errors, values)
        stored = docs.store(
            session,
            storage,
            keys,
            user,
            application,
            items[document.type],
            name,
            content,
            now=now,
        )
        field_values.write(session, keys, stored, dict(values), now=now)
        count += 1
    return count


def _document_file(
    data: RequirementData, demo: DemoFile, document, errors: list[str], values: dict
) -> tuple[str, bytes]:
    """The rendered image of the document, or a one-page SAMPLE PDF when there is none.

    There is no image when two chosen errors change the same document, or before the images
    have been rendered.
    """
    name = f"{demo.id}--{document.id}" + (f"--{errors[0]}" if len(errors) == 1 else "")
    image = IMAGE_DIR / f"{name}.jpg"
    if len(errors) <= 1 and image.is_file():
        return f"SAMPLE-{name}.jpg", image.read_bytes()
    type_title = data.catalog.document(document.type).title.en
    lines = [f"Application file: {demo.title.en}", ""] + [
        f"{field_id}: {value}" for field_id, value in values.items()
    ]
    return f"SAMPLE-{name}.pdf", sample_pdf(f"SAMPLE - {type_title}", lines)


def load(
    session: Session,
    storage: LocalStorage,
    keys: docs.Keys,
    email: str = DEFAULT_EMAIL,
    password: str | None = None,
    error_ids: list[str] | None = None,
    demos: list[DemoFile] | None = None,
    data: RequirementData | None = None,
) -> tuple[Loaded, list[str]]:
    """Replace the demo account's files; returns the summary and the stored files to remove.

    Flushes but does not commit; the caller removes the returned files after the commit.
    """
    email = service.normalise_email(email)
    if not is_reserved(email):
        raise DemoLoadError(
            f"{email} is not under a reserved example domain; the demo replaces the account's "
            "files, so it only uses addresses such as demo@visaassist.example."
        )
    data = data or load_requirement_data()
    demos = demos if demos is not None else load_all()
    error_ids = error_ids or []
    known = {e.id for demo in demos for e in demo.errors}
    unknown = sorted(set(error_ids) - known)
    if unknown:
        raise DemoLoadError(f"Unknown error IDs: {', '.join(unknown)}; see --list-errors.")
    set_id = queries.active_set_id(session)
    if set_id is None:
        raise DemoLoadError("No active requirement set; run `python -m app.requirements.seed`.")

    now = datetime.now(UTC)
    user, generated = _account(session, email, password)
    removed = _clear(session, user)
    docs.give_consent(session, user, now)
    loaded = Loaded(email=email, new_password=generated)
    for demo in demos:
        count = _add_file(session, storage, keys, data, user, set_id, demo, error_ids, now)
        applied = [e.id for e in demo.errors if e.id in error_ids]
        loaded.files.append((demo, applied, count))
    return loaded, removed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--email", default=DEFAULT_EMAIL)
    parser.add_argument(
        "--error", action="append", default=[], metavar="ID", help="apply a labelled error"
    )
    parser.add_argument("--list-errors", action="store_true", help="list the labelled errors")
    args = parser.parse_args(argv)

    if args.list_errors:
        for demo in load_all():
            for error in demo.errors:
                print(f"{error.id}  {demo.id:12}  {error.description}")
        return 0

    storage = get_storage()
    try:
        with Session(get_engine()) as session, session.begin():
            loaded, removed = load(
                session,
                storage,
                get_keys(),
                args.email,
                os.environ.get("DEMO_PASSWORD") or None,
                args.error,
            )
    except (DemoLoadError, service.AuthError, docs.DocumentError) as error:
        print(error, file=sys.stderr)
        return 1
    for key in removed:
        storage.delete(key)

    print(f"Demo account: {loaded.email}")
    if loaded.new_password:
        print(f"Password (shown once): {loaded.new_password}")
    for demo, applied, count in loaded.files:
        errors = ", ".join(applied) if applied else "none"
        print(f"  {demo.title.en}: {count} documents; errors applied: {errors}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

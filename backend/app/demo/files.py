"""Synthetic demo application files with labelled errors (`data/demo/`).

Each file holds documents that satisfy every rule of its destination and profile, and a list of
errors; each error changes one thing and names the finding it must produce. The files serve the
live demo and the fall success criterion: every injected error is reported, and the error-free
file gets no finding (docs/requirements.md, section 6).

No real person's data: every name, number and organisation is invented and the titles say SAMPLE.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

import yaml
from pydantic import Field, model_validator

from app.requirements.loader import RequirementData, load_requirement_data
from app.requirements.schema import Id, LocalizedText, Profile, Strict
from app.rules import engine
from app.rules.values import Value, normalise
from app.sources.registry import REPO_ROOT

DEMO_DIR = REPO_ROOT / "data" / "demo"


class DemoTrip(Strict):
    start: date
    end: date
    application_date: date


class DemoDocument(Strict):
    id: Id
    type: Id
    values: dict[str, object]


class SetValue(Strict):
    document: Id
    field: Id
    value: object = None  # null removes the value


class Change(Strict):
    remove: Id | None = None
    set: SetValue | None = None

    @model_validator(mode="after")
    def exactly_one(self) -> "Change":
        if (self.remove is None) == (self.set is None):
            raise ValueError("a change either removes a document or sets one value")
        return self


class Expect(Strict):
    """The finding an error must produce: a missing checklist item, or a failed rule and code."""

    missing: Id | None = None
    rule: Id | None = None
    code: str | None = None

    @model_validator(mode="after")
    def one_finding(self) -> "Expect":
        if (self.missing is None) == (self.rule is None) or (self.rule is None) != (
            self.code is None
        ):
            raise ValueError("expect either `missing`, or `rule` together with `code`")
        return self


class DemoError(Strict):
    id: str = Field(pattern=r"^[A-Z]\d{2}$")
    kind: str
    description: str
    change: Change
    expect: Expect


class DemoFile(Strict):
    id: Id
    title: LocalizedText
    destination: str = Field(pattern=r"^[A-Z]{2}$")
    profile: Profile
    trip: DemoTrip
    documents: list[DemoDocument] = Field(min_length=1)
    errors: list[DemoError] = Field(min_length=1)


@dataclass(frozen=True)
class Findings:
    """What the rule engine reports for a set of documents: missing items and failed rules."""

    missing: list[str]
    failed: dict[str, list[str]]  # rule ID → issue codes
    incomplete: list[str]

    def is_empty(self) -> bool:
        return not self.missing and not self.failed and not self.incomplete


def load_demo(path: Path, data: RequirementData | None = None) -> DemoFile:
    """Read a demo file and check every value against the field types of the catalogue."""
    with path.open(encoding="utf-8") as handle:
        demo = DemoFile.model_validate(yaml.safe_load(handle))
    data = data or load_requirement_data()
    documents_of(demo, data)  # raises ValueError on an unknown field or a value of the wrong form
    ids = {d.id for d in demo.documents}
    for error in demo.errors:
        target = error.change.remove or (error.change.set.document if error.change.set else None)
        if target not in ids:
            raise ValueError(f"{demo.id} {error.id}: unknown document {target}")
    return demo


def load_all(directory: Path = DEMO_DIR) -> list[DemoFile]:
    data = load_requirement_data()
    return [load_demo(path, data) for path in sorted(directory.glob("*.yaml"))]


def _stored(data: RequirementData, document_type: str, field_id: str, raw: object) -> Value:
    field = data.catalog.field(document_type, field_id)
    if field is None:
        raise ValueError(f"{document_type}.{field_id}: not a field of this document type")
    if isinstance(raw, date):
        raw = raw.isoformat()
    try:
        return normalise(field.type, raw)
    except ValueError as error:
        raise ValueError(f"{document_type}.{field_id}: {error}") from error


def changed(demo: DemoFile, changes: Sequence[Change] = ()) -> list[DemoDocument]:
    """The demo's documents with the given changes applied in order (raw values, as in YAML)."""
    documents = [d.model_copy(update={"values": dict(d.values)}) for d in demo.documents]
    for change in changes:
        if change.remove is not None:
            documents = [d for d in documents if d.id != change.remove]
        elif change.set is not None:
            for document in documents:
                if document.id == change.set.document:
                    document.values[change.set.field] = change.set.value
    return documents


def stored_values(data: RequirementData, document: DemoDocument) -> dict[str, Value]:
    """The document's values in the form the application stores them; null values are left out."""
    return {
        field_id: _stored(data, document.type, field_id, raw)
        for field_id, raw in document.values.items()
        if raw is not None
    }


def documents_of(
    demo: DemoFile, data: RequirementData, changes: Sequence[Change] = ()
) -> list[engine.Document]:
    """The demo's documents as the engine reads them, with the given changes applied."""
    return [
        engine.Document(id=d.id, type=d.type, values=stored_values(data, d))
        for d in changed(demo, changes)
    ]


def findings(demo: DemoFile, data: RequirementData, changes: Sequence[Change] = ()) -> Findings:
    ruleset = data.ruleset(demo.destination)
    documents = documents_of(demo, data, changes)
    trip = engine.Trip(demo.trip.start, demo.trip.end, demo.trip.application_date)
    required = {r.id: r.document for r in ruleset.checklist(demo.profile)}
    results = engine.evaluate(ruleset.rules_for(demo.profile), documents, trip)
    return Findings(
        missing=engine.missing_documents(required, documents),
        failed={
            r.rule_id: [issue.code for issue in r.issues] for r in results if r.status == "failed"
        },
        incomplete=[r.rule_id for r in results if r.status == "incomplete"],
    )


Outcome = Literal["detected", "missed", "detected with extra findings"]


@dataclass(frozen=True)
class ErrorResult:
    demo: str
    error: DemoError
    outcome: Outcome
    found: Findings


def evaluate_error(demo: DemoFile, error: DemoError, data: RequirementData) -> ErrorResult:
    """Apply one error to the clean file and compare the findings with its label."""
    found = findings(demo, data, [error.change])
    expect = error.expect
    if expect.missing is not None:
        hit = expect.missing in found.missing
        extra = bool(found.failed) or found.missing != [expect.missing] or bool(found.incomplete)
    else:
        hit = expect.code in found.failed.get(expect.rule or "", [])
        extra = set(found.failed) != {expect.rule} or bool(found.missing) or bool(found.incomplete)
    outcome: Outcome = (
        "missed" if not hit else ("detected with extra findings" if extra else "detected")
    )
    return ErrorResult(demo.id, error, outcome, found)

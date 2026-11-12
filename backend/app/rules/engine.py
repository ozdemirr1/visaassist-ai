"""Rule engine v0 (FR-09, FR-10): the checks of `data/requirements/` on entered field values.

Pure functions: no database, no clock. The caller gives the rules of the application's
requirement set, the uploaded documents with their field values, and the trip; every date is
compared with the trip or with the application date, never with "today", so a check gives the
same result whenever it is run.

A rule ends in one of four states:
- `passed`
- `failed`: an entered value breaks the rule
- `incomplete`: a value the rule needs has not been entered yet (or cannot be compared)
- `skipped`: none of the rule's documents is uploaded; the missing document is reported instead

Where one document type has several uploads, rules about age, confirmations and matching names
hold for every upload; rules about validity, amounts and periods hold if one upload satisfies
them (a passport scan and its copy need the expiry date only once).
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from typing import Literal, Protocol

from app.requirements import schema
from app.rules.values import Value

Status = Literal["passed", "failed", "incomplete", "skipped"]

# Tolerances the sources do not state; assumptions of this version (open question).
STATEMENT_MAX_AGE_MONTHS = 1  # a statement may end at most this long before the application
PAYSLIP_LATEST_WITHIN_MONTHS = 2  # the newest payslip is of the application month or the 2 before


@dataclass(frozen=True)
class Document:
    id: str
    type: str
    values: dict[str, Value]


@dataclass(frozen=True)
class Trip:
    start: date
    end: date
    application_date: date


@dataclass(frozen=True)
class Issue:
    """Why a rule did not pass: which document and field, the value found and the one expected."""

    code: str
    document_id: str | None = None
    document_type: str | None = None
    field: str | None = None
    value: object = None
    expected: object = None


@dataclass(frozen=True)
class Result:
    rule_id: str
    status: Status
    issues: list[Issue] = field(default_factory=list)


def add_months(day: date, months: int) -> date:
    """The same day `months` later (or earlier); the 31st becomes the month's last day."""
    index = day.year * 12 + day.month - 1 + months
    year, month = divmod(index, 12)
    month += 1
    for last in (day.day, 30, 29, 28):
        try:
            return date(year, month, last)
        except ValueError:
            continue
    raise ValueError(day)


def normalise_name(name: str) -> tuple[str, ...]:
    """Name parts without case, Turkish letters, punctuation or order.

    Bookings print `YILMAZ/AYSE`, passports `Ayşe Yılmaz`: both give ("ayse", "yilmaz").
    """
    table = str.maketrans("şŞıİğĞüÜöÖçÇâÂîÎûÛ", "sSiIgGuUoOcCaAiIuU")
    plain = name.translate(table).lower().replace("i̇", "i")
    cleaned = "".join(c if c.isalnum() else " " for c in plain)
    return tuple(sorted(cleaned.split()))


def normalise_code(value: str) -> str:
    """Document numbers without spaces, dashes or case."""
    return "".join(c for c in value.upper() if c.isalnum())


class Rule(Protocol):
    """What the engine reads of a rule: `schema.Rule` from the files or `LoadedRule` below."""

    @property
    def id(self) -> str: ...

    @property
    def check(self) -> schema.Check: ...


@dataclass(frozen=True)
class LoadedRule:
    """A rule read back from the database."""

    id: str
    check: schema.Check


def missing_documents(required: Mapping[str, str], documents: Sequence[Document]) -> list[str]:
    """IDs of the checklist items (item ID → document type) that have no uploaded document."""
    uploaded = {document.type for document in documents}
    return [item for item, document_type in required.items() if document_type not in uploaded]


def evaluate(rules: Sequence[Rule], documents: Sequence[Document], trip: Trip) -> list[Result]:
    return [_evaluate(rule, documents, trip) for rule in rules]


def _evaluate(rule: Rule, documents: Sequence[Document], trip: Trip) -> Result:
    check = rule.check
    run = _Run(documents, trip)
    if isinstance(check, schema.MaxAge):
        earliest = add_months(
            trip.application_date, -check.amount * (12 if check.unit == "years" else 1)
        )
        outcome = run.every(
            check.documents,
            lambda d: run.date_at_least(d, check.field, earliest, "too_old"),
        )
    elif isinstance(check, schema.ValidAfterTrip):
        needed = add_months(trip.end, check.months)
        outcome = run.any_one(
            [check.document],
            lambda d: run.date_at_least(d, check.field, needed, "expires_too_soon"),
        )
    elif isinstance(check, schema.MinValue):
        outcome = run.any_one([check.document], lambda d: run.min_value(d, check))
    elif isinstance(check, schema.MinAmount):
        outcome = run.any_one([check.document], lambda d: run.min_amount(d, check))
    elif isinstance(check, schema.FieldTrue):
        outcome = run.every(check.documents, lambda d: run.fields_true(d, check.fields))
    elif isinstance(check, schema.FieldsPresent):
        outcome = run.every([check.document], lambda d: run.fields_present(d, check.fields))
    elif isinstance(check, schema.PeriodCoversTrip):
        outcome = run.any_one([check.document], lambda d: run.covers_trip(d, check))
    elif isinstance(check, schema.CoversRecentMonths):
        outcome = run.any_one([check.document], lambda d: run.covers_recent(d, check))
    elif isinstance(check, schema.RecentMonthlyCount):
        outcome = run.monthly_count(check)
    elif isinstance(check, schema.NamesMatch | schema.ValuesMatch):
        same = normalise_name if isinstance(check, schema.NamesMatch) else normalise_code
        code = "name_differs" if isinstance(check, schema.NamesMatch) else "value_differs"
        outcome = run.matches(check, same, code)
    else:
        outcome = run.every(
            [d.type for d in documents if d.type not in check.exempt],
            lambda d: run.translated(d, check.languages),
        )
    return Result(rule.id, *outcome)


Outcome = tuple[Status, list[Issue]]
_WORST_FIRST: tuple[Status, ...] = ("failed", "incomplete", "passed")


class _Run:
    def __init__(self, documents: Sequence[Document], trip: Trip) -> None:
        self.documents = documents
        self.trip = trip

    def of_types(self, types: Sequence[str]) -> list[Document]:
        return [d for d in self.documents if d.type in types]

    # Combining the uploads of a rule's documents

    def every(self, types: Sequence[str], check: Callable[[Document], Outcome]) -> Outcome:
        """Every upload must pass: the worst outcome decides and all issues are reported."""
        outcomes = [check(d) for d in self.of_types(list(dict.fromkeys(types)))]
        if not outcomes:
            return "skipped", []
        status = next(s for s in _WORST_FIRST if any(o[0] == s for o in outcomes))
        return status, [issue for o in outcomes if o[0] != "passed" for issue in o[1]]

    def any_one(self, types: Sequence[str], check: Callable[[Document], Outcome]) -> Outcome:
        """One passing upload is enough; otherwise a failure counts before a missing value."""
        outcomes = [check(d) for d in self.of_types(types)]
        if not outcomes:
            return "skipped", []
        if any(o[0] == "passed" for o in outcomes):
            return "passed", []
        status: Status = "failed" if any(o[0] == "failed" for o in outcomes) else "incomplete"
        return status, [issue for o in outcomes if o[0] == status for issue in o[1]]

    # Reading values

    @staticmethod
    def issue(code: str, document: Document, field_id: str | None = None, **extra) -> Issue:
        return Issue(code, document.id, document.type, field_id, **extra)

    def missing(self, document: Document, field_id: str) -> Outcome:
        return "incomplete", [self.issue("value_missing", document, field_id)]

    @staticmethod
    def day(document: Document, field_id: str) -> date | None:
        value = document.values.get(field_id)
        return date.fromisoformat(value) if isinstance(value, str) else None

    # Checks on one document

    def date_at_least(self, document: Document, field_id: str, limit: date, code: str) -> Outcome:
        day = self.day(document, field_id)
        if day is None:
            return self.missing(document, field_id)
        if day < limit:
            return "failed", [
                self.issue(
                    code, document, field_id, value=day.isoformat(), expected=limit.isoformat()
                )
            ]
        return "passed", []

    def min_value(self, document: Document, check: schema.MinValue) -> Outcome:
        value = document.values.get(check.field)
        if not isinstance(value, int) or isinstance(value, bool):
            return self.missing(document, check.field)
        if value < check.value:
            return "failed", [
                self.issue(
                    "below_minimum", document, check.field, value=value, expected=check.value
                )
            ]
        return "passed", []

    def min_amount(self, document: Document, check: schema.MinAmount) -> Outcome:
        value = document.values.get(check.field)
        if not isinstance(value, dict):
            return self.missing(document, check.field)
        expected = {"amount": check.amount, "currency": check.currency}
        if value.get("currency") != check.currency:
            # No exchange rates in this version: the amount cannot be compared.
            return "incomplete", [
                self.issue("other_currency", document, check.field, value=value, expected=expected)
            ]
        amount = value.get("amount")
        if not isinstance(amount, int | float) or amount < check.amount:
            return "failed", [
                self.issue("amount_too_low", document, check.field, value=value, expected=expected)
            ]
        return "passed", []

    def fields_true(self, document: Document, fields: Sequence[str]) -> Outcome:
        issues: list[Issue] = []
        status: Status = "passed"
        for field_id in fields:
            value = document.values.get(field_id)
            if value is None:
                issues.append(self.issue("value_missing", document, field_id))
                status = "incomplete" if status == "passed" else status
            elif value is not True:
                issues.append(self.issue("not_confirmed", document, field_id, value=False))
                status = "failed"
        return status, [i for i in issues if status != "failed" or i.code == "not_confirmed"]

    def fields_present(self, document: Document, fields: Sequence[str]) -> Outcome:
        absent = [f for f in fields if document.values.get(f) is None]
        if not absent:
            return "passed", []
        if len(absent) == len(fields):
            # Nothing entered yet: the applicant has not reached this document.
            return "incomplete", [self.issue("value_missing", document, f) for f in absent]
        return "failed", [self.issue("not_stated", document, f) for f in absent]

    def covers_trip(self, document: Document, check: schema.PeriodCoversTrip) -> Outcome:
        start = self.day(document, check.start_field)
        end = self.day(document, check.end_field)
        if start is None or end is None:
            absent = check.start_field if start is None else check.end_field
            return self.missing(document, absent)
        issues = []
        if start > self.trip.start:
            issues.append(
                self.issue(
                    "period_starts_late",
                    document,
                    check.start_field,
                    value=start.isoformat(),
                    expected=self.trip.start.isoformat(),
                )
            )
        if end < self.trip.end:
            issues.append(
                self.issue(
                    "period_ends_early",
                    document,
                    check.end_field,
                    value=end.isoformat(),
                    expected=self.trip.end.isoformat(),
                )
            )
        return ("failed", issues) if issues else ("passed", [])

    def covers_recent(self, document: Document, check: schema.CoversRecentMonths) -> Outcome:
        """The period is at least N months long and ends shortly before the application."""
        start = self.day(document, check.start_field)
        end = self.day(document, check.end_field)
        if start is None or end is None:
            absent = check.start_field if start is None else check.end_field
            return self.missing(document, absent)
        issues = []
        latest_start = add_months(end, -check.months)
        if start > latest_start:
            issues.append(
                self.issue(
                    "period_too_short",
                    document,
                    check.start_field,
                    value=start.isoformat(),
                    expected=latest_start.isoformat(),
                )
            )
        earliest_end = add_months(self.trip.application_date, -STATEMENT_MAX_AGE_MONTHS)
        if end < earliest_end:
            issues.append(
                self.issue(
                    "period_not_recent",
                    document,
                    check.end_field,
                    value=end.isoformat(),
                    expected=earliest_end.isoformat(),
                )
            )
        return ("failed", issues) if issues else ("passed", [])

    # Checks across documents

    def monthly_count(self, check: schema.RecentMonthlyCount) -> Outcome:
        """One document for each of N months in a row, the newest close to the application."""
        documents = self.of_types([check.document])
        if not documents:
            return "skipped", []
        undated = [d for d in documents if self.day(d, check.date_field) is None]
        if undated:
            return "incomplete", [self.issue("value_missing", d, check.date_field) for d in undated]
        months = {
            (day.year, day.month)
            for d in documents
            if (day := self.day(d, check.date_field)) is not None
        }
        newest = max(months)
        applied = self.trip.application_date
        oldest_newest = add_months(applied.replace(day=1), -PAYSLIP_LATEST_WITHIN_MONTHS)
        if newest < (oldest_newest.year, oldest_newest.month):
            return "failed", [
                Issue(
                    "newest_too_old",
                    document_type=check.document,
                    field=check.date_field,
                    value=f"{newest[0]}-{newest[1]:02d}",
                    expected=f"{oldest_newest.year}-{oldest_newest.month:02d}",
                )
            ]
        first = date(newest[0], newest[1], 1)
        wanted = [add_months(first, -back) for back in range(check.months)]
        absent = [m for m in wanted if (m.year, m.month) not in months]
        if absent:
            return "failed", [
                Issue(
                    "month_missing",
                    document_type=check.document,
                    field=check.date_field,
                    value=f"{m.year}-{m.month:02d}",
                )
                for m in sorted(absent)
            ]
        return "passed", []

    def matches(
        self,
        check: schema.NamesMatch | schema.ValuesMatch,
        same: Callable[[str], object],
        code: str,
    ) -> Outcome:
        """Fields on other documents equal the reference field (the passport's)."""
        compared = [
            (d, field_id)
            for target in check.compare
            for d in self.of_types([target.split(".")[0]])
            for field_id in [target.split(".")[1]]
        ]
        if not compared:
            return "skipped", []
        reference_type, reference_field = check.reference.split(".")
        references = [
            value
            for d in self.of_types([reference_type])
            if isinstance(value := d.values.get(reference_field), str)
        ]
        if not references:
            return "incomplete", [
                Issue("reference_missing", document_type=reference_type, field=reference_field)
            ]
        accepted = {same(value) for value in references}
        issues: list[Issue] = []
        status: Status = "passed"
        for document, field_id in compared:
            value = document.values.get(field_id)
            if not isinstance(value, str):
                issues.append(self.issue("value_missing", document, field_id))
                status = "incomplete" if status == "passed" else status
            elif same(value) not in accepted:
                issues.append(
                    self.issue(code, document, field_id, value=value, expected=references[0])
                )
                status = "failed"
        return status, [i for i in issues if status != "failed" or i.code == code]

    def translated(self, document: Document, languages: Sequence[str]) -> Outcome:
        language = document.values.get("language")
        if not isinstance(language, str):
            return self.missing(document, "language")
        if language in languages or document.values.get("translation_language") in languages:
            return "passed", []
        return "failed", [
            self.issue(
                "translation_missing",
                document,
                "translation_language",
                value=language,
                expected=list(languages),
            )
        ]

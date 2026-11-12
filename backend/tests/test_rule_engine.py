"""Rule engine v0 on synthetic application files (FR-09, FR-10).

The rules are the repository's own (`data/requirements/`); the documents are invented. `complete`
is a file on which every rule passes; each test changes one thing and names the rule that reacts.
"""

from datetime import date

import pytest

from app.requirements.loader import load_requirement_data
from app.rules import engine
from app.rules.engine import Document, Trip, add_months, normalise_name

DATA = load_requirement_data()
TRIP = Trip(start=date(2027, 4, 10), end=date(2027, 4, 20), application_date=date(2027, 3, 1))
NAME = "Ayşe Yılmaz"


def complete() -> dict[str, Document]:
    """An employed applicant's file for the Netherlands with nothing wrong, by short name."""
    documents = {
        "form": Document("d-form", "application_form", {"signed": True}),
        "passport": Document(
            "d-passport",
            "passport",
            {
                "full_name": NAME,
                "passport_number": "U12345678",
                "issue_date": "2022-05-01",
                "expiry_date": "2032-05-01",
                "blank_pages": 10,
                "signed": True,
            },
        ),
        "photo": Document("d-photo", "photo", {"taken_on": "2027-01-15"}),
        "registry": Document(
            "d-registry",
            "civil_registry_extract",
            {"full_name": NAME, "issue_date": "2027-02-10"},
        ),
        "flight": Document(
            "d-flight",
            "travel_reservation",
            {
                "passenger_name": "YILMAZ/AYSE",
                "departure_date": "2027-04-10",
                "return_date": "2027-04-20",
            },
        ),
        "hotel": Document(
            "d-hotel",
            "accommodation",
            {"guest_name": NAME, "check_in": "2027-04-10", "check_out": "2027-04-20"},
        ),
        "bank": Document(
            "d-bank",
            "bank_statement",
            {
                "holder_name": "AYSE YILMAZ",
                "period_start": "2026-11-25",
                "period_end": "2027-02-25",
                "issue_date": "2027-02-25",
            },
        ),
        "letter": Document(
            "d-letter",
            "employer_letter",
            {
                "employee_name": NAME,
                "passport_number": "u 1234 5678",
                "addressed_to_consulate": True,
                "employment_start": "2021-09-01",
                "job_title": "Muhasebe uzmanı",
                "leave_start": "2027-04-09",
                "leave_end": "2027-04-21",
                "leave_paid": False,
                "employer_contact": "Örnek A.Ş., İstanbul",
                "signatory_name": "Mehmet Demir, İK Müdürü",
                "issue_date": "2027-02-20",
            },
        ),
        "sgk1": Document(
            "d-sgk1",
            "sgk_employment_declaration",
            {"full_name": NAME, "issue_date": "2027-02-20", "qr_code_readable": True},
        ),
        "sgk2": Document(
            "d-sgk2",
            "sgk_service_record",
            {"full_name": NAME, "issue_date": "2027-02-20", "qr_code_readable": True},
        ),
        "insurance": Document(
            "d-insurance",
            "travel_insurance",
            {
                "insured_name": NAME,
                "coverage_start": "2027-04-10",
                "coverage_end": "2027-04-20",
                "coverage_amount": {"amount": 30000.0, "currency": "EUR"},
                "covers_all_schengen": True,
                "covers_repatriation": True,
            },
        ),
    }
    for month in ("2026-12", "2027-01", "2027-02"):
        documents[f"payslip-{month}"] = Document(
            f"d-payslip-{month}",
            "payslip",
            {"employee_name": NAME, "pay_month": f"{month}-28", "issue_date": f"{month}-28"},
        )
    return documents


def with_value(documents: dict[str, Document], name: str, field: str, value) -> dict:
    document = documents[name]
    values = {k: v for k, v in document.values.items() if k != field}
    if value is not None:
        values[field] = value
    return {**documents, name: Document(document.id, document.type, values)}


def run(documents: dict[str, Document], destination: str = "NL", profile: str = "employed"):
    rules = DATA.ruleset(destination).rules_for(profile)
    results = engine.evaluate(rules, list(documents.values()), TRIP)
    return {result.rule_id: result for result in results}


def required() -> dict[str, str]:
    return {r.id: r.document for r in DATA.ruleset("NL").checklist("employed")}


def codes(result: engine.Result) -> list[str]:
    return [issue.code for issue in result.issues]


def test_a_complete_file_passes_every_rule() -> None:
    results = run(complete())
    assert len(results) == 16
    assert {r.status for r in results.values()} == {"passed"}
    assert engine.missing_documents(required(), list(complete().values())) == []


def test_an_empty_file_misses_every_document_and_skips_every_rule() -> None:
    assert len(engine.missing_documents(required(), [])) == 12
    only_passport = [complete()["passport"]]
    assert "nl-req-passport" not in engine.missing_documents(required(), only_passport)
    assert {r.status for r in run({}).values()} == {"skipped"}


def test_an_uploaded_document_without_values_is_incomplete_not_failed() -> None:
    documents = {**complete(), "passport": Document("d-passport", "passport", {})}
    results = run(documents)
    for rule in (
        "nl-rule-passport-issued-within-10-years",
        "nl-rule-passport-validity",
        "nl-rule-passport-blank-pages",
        "nl-rule-passport-signed",
    ):
        assert results[rule].status == "incomplete", rule
        assert codes(results[rule]) == ["value_missing"]
    assert results["eu-rule-names-match"].status == "incomplete"
    assert codes(results["eu-rule-names-match"]) == ["reference_missing"]


@pytest.mark.parametrize(
    ("name", "field", "value", "rule", "code", "expected"),
    [
        (
            "passport",
            "issue_date",
            "2017-02-28",
            "nl-rule-passport-issued-within-10-years",
            "too_old",
            "2017-03-01",
        ),
        (
            "passport",
            "expiry_date",
            "2027-07-19",
            "nl-rule-passport-validity",
            "expires_too_soon",
            "2027-07-20",
        ),
        ("passport", "blank_pages", 1, "nl-rule-passport-blank-pages", "below_minimum", 2),
        ("passport", "signed", False, "nl-rule-passport-signed", "not_confirmed", None),
        ("photo", "taken_on", "2026-08-31", "nl-rule-photo-age", "too_old", "2026-09-01"),
        (
            "insurance",
            "coverage_amount",
            {"amount": 25000.0, "currency": "EUR"},
            "nl-rule-insurance-amount",
            "amount_too_low",
            {"amount": 30000.0, "currency": "EUR"},
        ),
        (
            "insurance",
            "coverage_end",
            "2027-04-19",
            "nl-rule-insurance-period",
            "period_ends_early",
            "2027-04-20",
        ),
        (
            "insurance",
            "coverage_start",
            "2027-04-11",
            "nl-rule-insurance-period",
            "period_starts_late",
            "2027-04-10",
        ),
        (
            "insurance",
            "covers_repatriation",
            False,
            "nl-rule-insurance-territory-and-repatriation",
            "not_confirmed",
            None,
        ),
        (
            "letter",
            "leave_end",
            "2027-04-18",
            "eu-rule-leave-covers-trip",
            "period_ends_early",
            "2027-04-20",
        ),
        (
            "letter",
            "addressed_to_consulate",
            False,
            "eu-rule-employer-letter-addressed",
            "not_confirmed",
            None,
        ),
        ("letter", "job_title", None, "eu-rule-employer-letter-contents", "not_stated", None),
        (
            "letter",
            "passport_number",
            "U87654321",
            "eu-rule-passport-number-matches",
            "value_differs",
            "U12345678",
        ),
        ("sgk2", "qr_code_readable", False, "eu-rule-sgk-qr-readable", "not_confirmed", None),
        (
            "bank",
            "period_start",
            "2026-12-20",
            "eu-rule-bank-statement-period",
            "period_too_short",
            "2026-11-25",
        ),
        (
            "bank",
            "period_end",
            "2027-01-20",
            "eu-rule-bank-statement-period",
            "period_not_recent",
            "2027-02-01",
        ),
        ("hotel", "guest_name", "Ayşe Kaya", "eu-rule-names-match", "name_differs", NAME),
    ],
)
def test_one_wrong_value_fails_exactly_its_rule(name, field, value, rule, code, expected) -> None:
    results = run(with_value(complete(), name, field, value))
    failed = {rule_id for rule_id, result in results.items() if result.status != "passed"}
    assert failed == {rule}
    result = results[rule]
    assert result.status == "failed"
    assert code in codes(result)
    issue = next(i for i in result.issues if i.code == code)
    assert issue.document_id == complete()[name].id and issue.field == field
    assert issue.expected == expected


def test_amount_in_another_currency_cannot_be_compared() -> None:
    documents = with_value(
        complete(), "insurance", "coverage_amount", {"amount": 1_500_000.0, "currency": "TRY"}
    )
    result = run(documents)["nl-rule-insurance-amount"]
    assert result.status == "incomplete" and codes(result) == ["other_currency"]


def test_a_missing_month_of_payslips_is_named() -> None:
    documents = complete()
    del documents["payslip-2027-01"]
    result = run(documents)["eu-rule-payslips-last-3-months"]
    assert result.status == "failed"
    assert [(i.code, i.value) for i in result.issues] == [("month_missing", "2027-01")]


def test_payslips_that_stop_long_before_the_application_fail() -> None:
    documents = {k: v for k, v in complete().items() if not k.startswith("payslip")}
    for month in ("2026-08", "2026-09", "2026-10"):
        documents[f"payslip-{month}"] = Document(
            f"d-{month}", "payslip", {"employee_name": NAME, "pay_month": f"{month}-28"}
        )
    result = run(documents)["eu-rule-payslips-last-3-months"]
    assert result.status == "failed"
    assert [(i.code, i.value, i.expected) for i in result.issues] == [
        ("newest_too_old", "2026-10", "2027-01")
    ]


def test_a_second_upload_of_the_same_document_does_not_need_its_own_values() -> None:
    documents = {**complete(), "copy": Document("d-copy", "passport", {})}
    results = run(documents)
    assert results["nl-rule-passport-validity"].status == "passed"  # one upload is enough
    assert results["nl-rule-passport-blank-pages"].status == "passed"
    assert results["nl-rule-passport-signed"].status == "incomplete"  # asked of every upload


def test_students_are_not_checked_against_employee_rules() -> None:
    results = run(complete(), profile="student")
    assert "eu-rule-payslips-last-3-months" not in results
    assert results["eu-rule-yok-qr-readable"].status == "skipped"


def test_norway_asks_for_translations_except_of_passport_photo_and_form() -> None:
    documents = {
        name: Document(d.id, d.type, {**d.values, "language": "tr"})
        for name, d in complete().items()
    }
    result = run(documents, destination="NO")["no-rule-translation"]
    assert result.status == "failed"
    flagged = {issue.document_type for issue in result.issues}
    assert flagged.isdisjoint({"passport", "photo", "application_form"})
    assert "bank_statement" in flagged and len(result.issues) == 11

    translated = {
        name: Document(d.id, d.type, {**d.values, "translation_language": "en"})
        for name, d in documents.items()
    }
    assert run(translated, destination="NO")["no-rule-translation"].status == "passed"

    unknown = with_value(translated, "bank", "language", None)
    result = run(unknown, destination="NO")["no-rule-translation"]
    assert result.status == "incomplete" and codes(result) == ["value_missing"]


def test_norway_refuses_supporting_documents_older_than_six_months() -> None:
    documents = with_value(complete(), "registry", "issue_date", "2026-08-31")
    result = run(documents, destination="NO")["no-rule-document-age"]
    assert result.status == "failed"
    assert [(i.document_id, i.expected) for i in result.issues] == [("d-registry", "2026-09-01")]


@pytest.mark.parametrize(
    ("day", "months", "expected"),
    [
        (date(2027, 3, 1), -6, date(2026, 9, 1)),
        (date(2027, 3, 31), -1, date(2027, 2, 28)),
        (date(2028, 1, 31), 1, date(2028, 2, 29)),
        (date(2027, 4, 20), 3, date(2027, 7, 20)),
        (date(2027, 1, 15), -120, date(2017, 1, 15)),
    ],
)
def test_add_months_keeps_the_day_or_takes_the_last_of_the_month(day, months, expected) -> None:
    assert add_months(day, months) == expected


@pytest.mark.parametrize(
    "written",
    ["Ayşe Yılmaz", "AYSE YILMAZ", "YILMAZ/AYSE", "yılmaz, ayşe", "AYŞE  YILMAZ", "Yilmaz Ayse"],
)
def test_names_match_across_case_turkish_letters_and_order(written: str) -> None:
    assert normalise_name(written) == ("ayse", "yilmaz")


def test_a_missing_middle_name_is_a_difference() -> None:
    assert normalise_name("Ayşe Nur Yılmaz") != normalise_name("Ayşe Yılmaz")

import shutil
from collections.abc import Callable
from pathlib import Path

import pytest
import yaml

from app.requirements.loader import (
    REQUIREMENTS_DIR,
    RequirementData,
    RequirementDataError,
    load_requirement_data,
)

Mutation = Callable[[dict], None]


@pytest.fixture(scope="module")
def data() -> RequirementData:
    return load_requirement_data()


def load_with_change(tmp_path: Path, file_name: str, change: Mutation) -> RequirementData:
    """Copy the repository's requirement files, change one of them and load the copy."""
    directory = tmp_path / "requirements"
    shutil.copytree(REQUIREMENTS_DIR, directory)
    path = directory / file_name
    content = yaml.safe_load(path.read_text(encoding="utf-8"))
    change(content)
    path.write_text(yaml.safe_dump(content, allow_unicode=True), encoding="utf-8")
    return load_requirement_data(directory)


def rule(content: dict, rule_id: str) -> dict:
    return next(r for r in content["rules"] if r["id"] == rule_id)


# The repository's data


def test_repository_data_is_consistent(data: RequirementData) -> None:
    assert data.destinations == ["NL", "NO"]


@pytest.mark.parametrize("destination", ["NL", "NO"])
def test_checklists_follow_the_profile(data: RequirementData, destination: str) -> None:
    ruleset = data.ruleset(destination)
    employed = {r.document for r in ruleset.checklist("employed")}
    student = {r.document for r in ruleset.checklist("student")}

    common = {"passport", "photo", "application_form", "travel_insurance", "bank_statement"}
    assert common <= employed & student
    assert {"payslip", "employer_letter", "sgk_service_record"} <= employed - student
    assert "yok_student_certificate" in student - employed


def test_translation_rule_applies_only_to_norway(data: RequirementData) -> None:
    def kinds(destination: str) -> set[str]:
        return {r.check.kind for r in data.ruleset(destination).rules}

    assert "translation_present" in kinds("NO")
    assert "translation_present" not in kinds("NL")


def test_payslip_rule_cites_the_eu_baseline(data: RequirementData) -> None:
    [payslip_rule] = [r for r in data.ruleset("NL").rules if r.check.kind == "recent_monthly_count"]

    assert payslip_rule.source.source_id == "eu-harmonised-list-tr"


def test_every_title_has_both_languages(data: RequirementData) -> None:
    titles = [r.title for layer in data.layers for r in layer.rules]
    titles += [d.title for d in data.catalog.document_types]

    assert all(t.en.strip() and t.tr.strip() for t in titles)


# Inconsistencies are reported


def test_unknown_source_is_reported(tmp_path: Path) -> None:
    def change(content: dict) -> None:
        rule(content, "nl-rule-photo-age")["source"]["source_id"] = "nl-missing-page"

    with pytest.raises(RequirementDataError, match="unknown source 'nl-missing-page'"):
        load_with_change(tmp_path, "nl.yaml", change)


def test_source_of_another_destination_is_reported(tmp_path: Path) -> None:
    def change(content: dict) -> None:
        rule(content, "nl-rule-photo-age")["source"]["source_id"] = "no-checklist-c-visa-tr"

    with pytest.raises(RequirementDataError, match="cites a NO source in the NL layer"):
        load_with_change(tmp_path, "nl.yaml", change)


def test_unknown_field_is_reported(tmp_path: Path) -> None:
    def change(content: dict) -> None:
        rule(content, "nl-rule-photo-age")["check"]["field"] = "taken_on_place"

    with pytest.raises(RequirementDataError, match="photo has no field 'taken_on_place'"):
        load_with_change(tmp_path, "nl.yaml", change)


def test_field_of_the_wrong_type_is_reported(tmp_path: Path) -> None:
    def change(content: dict) -> None:
        rule(content, "nl-rule-insurance-amount")["check"]["field"] = "insured_name"

    with pytest.raises(RequirementDataError, match="insured_name is text, min_amount needs money"):
        load_with_change(tmp_path, "nl.yaml", change)


def test_id_with_the_wrong_prefix_is_reported(tmp_path: Path) -> None:
    def change(content: dict) -> None:
        rule(content, "nl-rule-photo-age")["id"] = "no-rule-photo-age"

    with pytest.raises(RequirementDataError, match="id must start with 'nl-'"):
        load_with_change(tmp_path, "nl.yaml", change)


def test_rule_without_a_checklist_item_is_reported(tmp_path: Path) -> None:
    def change(content: dict) -> None:
        content["requirements"] = [
            r for r in content["requirements"] if r["document"] != "travel_insurance"
        ]

    with pytest.raises(RequirementDataError, match="does not ask for 'travel_insurance'"):
        load_with_change(tmp_path, "nl.yaml", change)

"""Comparing the model alone with the model plus rules (app.demo.compare); no model call."""

import json

from app.ai.extraction import Extraction
from app.demo.compare import (
    MANIFEST,
    Case,
    Outcome,
    cases,
    concerned_type,
    images_for,
    score_alone,
    score_rules,
    specs_for,
    summary,
)
from app.demo.files import load_all, stored_values
from app.requirements.loader import load_requirement_data
from app.rules import engine

DATA = load_requirement_data()
DEMOS = {d.id: d for d in load_all()}
ALL = {c.name: c for c in cases(list(DEMOS.values()))}
MANIFEST_ROWS = json.loads(MANIFEST.read_text(encoding="utf-8"))


def truth_documents(case: Case) -> list[engine.Document]:
    """The documents as the model would read them if it read every value right."""
    return [
        engine.Document(id=d.id, type=d.type, values=stored_values(DATA, d))
        for d, _ in images_for(case, MANIFEST_ROWS)
    ]


def test_there_are_two_clean_cases_and_seventeen_errors() -> None:
    assert len(ALL) == 19 and sum(c.error is None for c in ALL.values()) == 2


def test_an_error_case_uses_the_error_image_and_drops_a_removed_document() -> None:
    images = dict((d.id, i) for d, i in images_for(ALL["employed-nl:E06"], MANIFEST_ROWS))
    assert any("--E06" in image for image in images.values())
    removed = ALL["student-no:S04"]
    kept = [d.id for d, _ in images_for(removed, MANIFEST_ROWS)]
    assert removed.error.change.remove not in kept


def test_perfect_reading_gives_the_rules_every_error_and_no_false_alarm() -> None:
    for case in ALL.values():
        outcome = Outcome(1, "model + rules", case.name, None, None, None)
        score_rules(case, DATA, truth_documents(case), outcome)
        assert outcome.found in (None, True), case.name
        assert outcome.false_alarms == [], case.name


def test_the_model_alone_is_scored_by_the_document_it_names() -> None:
    case = ALL["employed-nl:E06"]
    target = concerned_type(case)
    outcome = Outcome(1, "model alone", case.name, "E06", None, None)
    problems = [
        {"document_type": target, "problem": "name differs from the passport"},
        {"document_type": "photo", "problem": "photo may be too old"},
    ]
    score_alone(case, DATA, problems, outcome)
    assert outcome.found is True and outcome.false_alarms == ["photo: photo may be too old"]
    text = summary([outcome], errors=1, clean=0)
    assert "errors found per run: [1] of 1" in text


def test_language_fields_are_asked_only_where_a_translation_rule_reads_them() -> None:
    norway, netherlands = ALL["student-no:clean"], ALL["employed-nl:clean"]
    assert "language" in {s.id for s in specs_for(DATA, norway, "bank_statement")}
    assert "language" not in {s.id for s in specs_for(DATA, norway, "passport")}
    assert "language" not in {s.id for s in specs_for(DATA, netherlands, "bank_statement")}
    assert isinstance(Extraction(values={}, confidence={}), Extraction)

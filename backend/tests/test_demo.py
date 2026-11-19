"""The demo files: clean files give no finding, every labelled error is reported (fall criterion).

The files are synthetic (`data/demo/`); these tests run the rule engine only, no database.
"""

import pytest

from app.demo.files import (
    DEMO_DIR,
    Change,
    DemoError,
    Expect,
    SetValue,
    evaluate_error,
    findings,
    load_all,
    load_demo,
)
from app.requirements.loader import load_requirement_data

DATA = load_requirement_data()
DEMOS = load_all()
ERRORS = [(demo, error) for demo in DEMOS for error in demo.errors]


def test_there_is_a_demo_file_for_each_profile_and_both_destinations() -> None:
    assert {(d.profile, d.destination) for d in DEMOS} == {("employed", "NL"), ("student", "NO")}
    for demo in DEMOS:
        assert demo.title.en.startswith("SAMPLE") and demo.title.tr.startswith("ÖRNEK")


@pytest.mark.parametrize("demo", DEMOS, ids=lambda d: d.id)
def test_a_clean_demo_file_gives_no_finding(demo) -> None:
    assert findings(demo, DATA).is_empty()


@pytest.mark.parametrize(("demo", "error"), ERRORS, ids=lambda x: getattr(x, "id", ""))
def test_every_labelled_error_is_reported_and_nothing_else(demo, error) -> None:
    result = evaluate_error(demo, error, DATA)
    assert result.outcome == "detected", result.found


def test_a_wrong_label_counts_as_missed() -> None:
    demo = DEMOS[0]
    wrong = DemoError(
        id="X01",
        kind="test",
        description="Changes the photo date but expects a passport finding.",
        change=Change(set=SetValue(document="photo", field="taken_on", value="2026-07-01")),
        expect=Expect(rule="nl-rule-passport-validity", code="expires_too_soon"),
    )
    assert evaluate_error(demo, wrong, DATA).outcome == "missed"


def test_a_value_of_the_wrong_form_is_refused(tmp_path) -> None:
    path = tmp_path / "bad.yaml"
    source = (DEMO_DIR / "employed-nl.yaml").read_text(encoding="utf-8")
    path.write_text(source.replace("blank_pages: 10", 'blank_pages: "ten"'), encoding="utf-8")
    with pytest.raises(ValueError, match="blank_pages"):
        load_demo(path, DATA)

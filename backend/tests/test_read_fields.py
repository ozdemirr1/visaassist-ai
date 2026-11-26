"""Scoring the fields the model read from the demo images (app.demo.read_fields); no model call."""

from app.ai.extraction import Extraction
from app.demo.read_fields import ImageResult, same, score, specs_for, summary
from app.requirements.loader import load_requirement_data

DATA = load_requirement_data()
PASSPORT = {
    "file": "employed-nl",
    "document": "passport",
    "type": "passport",
    "error": None,
    "image": "employed-nl--passport.jpg",
    "values": {
        "full_name": "Deniz Örnek",
        "passport_number": "U00000001",
        "issue_date": "2022-05-01",
        "expiry_date": "2032-05-01",
        "blank_pages": 10,
        "signed": True,
    },
}


def test_values_are_compared_as_the_rule_engine_compares_them() -> None:
    assert same("text", "Deniz Örnek", "ORNEK DENIZ")
    assert not same("text", "Deniz Örnek", "Deniz Ornekk")
    assert same("text", "U00000001", "U 0000 0001")
    assert same(
        "money", {"amount": 30000.0, "currency": "EUR"}, {"amount": 30000, "currency": "EUR"}
    )
    assert not same(
        "money", {"amount": 30000.0, "currency": "EUR"}, {"amount": 30000, "currency": "TRY"}
    )
    assert same("date", "2022-05-01", "2022-05-01") and not same("date", "2022-05-01", None)


def test_only_the_stated_values_are_scored_and_extra_ones_are_counted() -> None:
    specs = specs_for(DATA, "passport", PASSPORT["values"])
    assert {s.id for s in specs} >= set(PASSPORT["values"])
    read = {**PASSPORT["values"], "full_name": "DENIZ ORNEK", "signed": False}
    result = Extraction(values=read, confidence=dict.fromkeys(read, 0.9))
    image = ImageResult("employed-nl--passport.jpg", "passport", None, 1, "m", "v")
    score(DATA, PASSPORT, result, image)
    assert [f.field for f in image.fields if not f.correct] == ["signed"]
    assert len(image.fields) == 6 and image.unexpected == []
    text = summary([image])
    assert "fields correct: 5 / 6 (83.3%)" in text and "wrong 1x passport.signed" in text

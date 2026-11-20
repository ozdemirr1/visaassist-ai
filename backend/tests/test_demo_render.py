"""The demo documents drawn as images for field extraction (`app.demo.render`, ADR 0007).

These tests check the HTML and the manifest; the images themselves are made by
tools/demo-documents with a browser and are compared through the manifest.
"""

import json

import pytest

from app.demo.files import changed, load_all, stored_values
from app.demo.render import OUT_DIR, latin, mrz, mrz_check, render_all, render_document
from app.requirements.loader import load_requirement_data

DATA = load_requirement_data()
DEMOS = load_all()


def test_mrz_check_digits_follow_icao_9303() -> None:
    # The specimen of ICAO Doc 9303, part 4: document number, birth and expiry dates.
    assert mrz_check("L898902C3") == "6"
    assert mrz_check("740812") == "2"
    assert mrz_check("120415") == "9"
    line1, line2 = mrz("Örnek", "Deniz", "U00000001", "1994-06-12", "M", "2032-05-01")
    assert line1.startswith("P<TURORNEK<<DENIZ<") and len(line1) == len(line2) == 44
    assert line2.startswith("U000000011TUR9406122M3205013")


def test_turkish_letters_are_written_without_marks_where_bookings_do() -> None:
    assert latin("Çağrı Şükrü Öztürk İnce") == "CAGRI SUKRU OZTURK INCE"


@pytest.mark.parametrize(
    ("demo", "document"),
    [(demo, doc) for demo in DEMOS for doc in demo.documents],
    ids=lambda x: getattr(x, "id", ""),
)
def test_every_document_is_marked_sample_and_shows_its_text_values(demo, document) -> None:
    html, _ = render_document(demo, document, DATA)
    assert "SAMPLE" in html
    for field, value in stored_values(DATA, document).items():
        if isinstance(value, str) and field.endswith("name"):
            parts = value.replace("/", " ").split()  # a name may be printed in parts
            assert all(p in html or latin(p) in html for p in parts), f"{document.id}.{field}"


def test_an_error_image_shows_the_changed_value() -> None:
    demo = next(d for d in DEMOS if d.id == "employed-nl")
    error = next(e for e in demo.errors if e.id == "E06")
    hotel = next(d for d in changed(demo, [error.change]) if d.id == "hotel")
    html, _ = render_document(demo, hotel, DATA)
    assert "Deniz Başka" in html


def test_a_translation_is_a_second_page_and_its_absence_removes_it() -> None:
    demo = next(d for d in DEMOS if d.id == "student-no")
    bank = next(d for d in demo.documents if d.id == "bank")
    with_translation, _ = render_document(demo, bank, DATA)
    error = next(e for e in demo.errors if e.id == "S01")
    without = next(d for d in changed(demo, [error.change]) if d.id == "bank")
    without_translation, _ = render_document(demo, without, DATA)
    assert with_translation.count('class="page"') == 2
    assert without_translation.count('class="page"') == 1


def test_the_manifest_has_one_image_per_document_and_value_changing_error(tmp_path) -> None:
    manifest = render_all(tmp_path)
    documents = sum(len(d.documents) for d in DEMOS)
    value_errors = sum(1 for d in DEMOS for e in d.errors if e.change.set is not None)
    assert len(manifest) == documents + value_errors
    assert len({m["image"] for m in manifest}) == len(manifest)
    assert len(list((tmp_path / "html").glob("*.html"))) == len(manifest)


def test_the_committed_manifest_matches_the_demo_files(tmp_path) -> None:
    committed = OUT_DIR / "manifest.json"
    if not committed.exists():
        pytest.skip("images not rendered yet")
    entries = json.loads(committed.read_text(encoding="utf-8"))
    for entry in entries:
        assert (OUT_DIR / entry["image"]).is_file(), entry["image"]
    fresh = render_all(tmp_path)
    assert entries == fresh, "demo files or templates changed: render the images again"

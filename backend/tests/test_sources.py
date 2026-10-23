from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from app.sources.registry import Registry, Source, load_registry
from app.sources.snapshot import read_manifest, run

NOW = datetime(2026, 10, 26, 9, 0, 0, tzinfo=UTC)
LATER = datetime(2026, 11, 2, 9, 0, 0, tzinfo=UTC)


def make_source(**overrides: object) -> Source:
    fields: dict[str, object] = {
        "id": "nl-test",
        "title": "Test checklist",
        "publisher": "Test publisher",
        "layer": "national",
        "destination": "NL",
        "url": "https://example.org/checklist",
        "format": "html",
        "reviewed_on": "2026-10-23",
    }
    fields.update(overrides)
    return Source.model_validate(fields)


def client_returning(*bodies: bytes, status_code: int = 200) -> httpx.Client:
    responses = iter(bodies)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code, content=next(responses), headers={"content-type": "text/html"}
        )

    return httpx.Client(transport=httpx.MockTransport(handler))


# Registry


def test_repository_registry_is_valid() -> None:
    registry = load_registry()

    assert {s.destination for s in registry.sources if s.layer == "national"} == {"NL", "NO"}
    assert any(s.layer == "eu" for s in registry.sources)


def test_national_source_needs_destination() -> None:
    with pytest.raises(ValidationError, match="destination"):
        make_source(destination=None)


def test_eu_source_has_no_destination() -> None:
    with pytest.raises(ValidationError, match="every destination"):
        make_source(layer="eu", destination="NL")


def test_source_url_must_use_https() -> None:
    with pytest.raises(ValidationError, match="HTTPS"):
        make_source(url="http://example.org/checklist")


def test_duplicate_source_ids_are_rejected() -> None:
    source = make_source().model_dump()

    with pytest.raises(ValidationError, match="duplicate source ids: nl-test"):
        Registry.model_validate({"sources": [source, source]})


# Snapshots


def test_first_snapshot_is_stored(tmp_path: Path) -> None:
    [record] = run([make_source()], tmp_path, client_returning(b"<p>v1</p>"), now=NOW)

    assert record.status == "new"
    assert record.file is not None
    assert (tmp_path / record.file).read_bytes() == b"<p>v1</p>"
    assert read_manifest(tmp_path) == [record]


def test_unchanged_content_is_recorded_but_not_stored_again(tmp_path: Path) -> None:
    source = make_source()
    run([source], tmp_path, client_returning(b"<p>v1</p>"), now=NOW)

    [record] = run([source], tmp_path, client_returning(b"<p>v1</p>"), now=LATER)

    assert record.status == "unchanged"
    assert record.file is None
    assert len(list((tmp_path / source.id).iterdir())) == 1
    assert len(read_manifest(tmp_path)) == 2


def test_changed_content_is_stored_as_a_new_version(tmp_path: Path) -> None:
    source = make_source()
    [first] = run([source], tmp_path, client_returning(b"<p>v1</p>"), now=NOW)

    [second] = run([source], tmp_path, client_returning(b"<p>v2</p>"), now=LATER)

    assert second.status == "changed"
    assert second.sha256 != first.sha256
    assert len(list((tmp_path / source.id).iterdir())) == 2


def test_http_error_is_recorded_without_a_file(tmp_path: Path) -> None:
    [record] = run([make_source()], tmp_path, client_returning(b"gone", status_code=404), now=NOW)

    assert record.status == "error"
    assert record.http_status == 404
    assert record.file is None
    assert not (tmp_path / "nl-test").exists()

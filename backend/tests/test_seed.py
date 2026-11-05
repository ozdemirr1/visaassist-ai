"""The requirement set id: a fingerprint of the files that define the set."""

import shutil
from pathlib import Path

from app.requirements.loader import REQUIREMENTS_DIR
from app.requirements.seed import requirement_set_id
from app.sources.registry import DEFAULT_REGISTRY


def copy_files(tmp_path: Path) -> tuple[Path, Path]:
    directory = tmp_path / "requirements"
    shutil.copytree(REQUIREMENTS_DIR, directory)
    registry = tmp_path / "sources.yaml"
    shutil.copy(DEFAULT_REGISTRY, registry)
    return directory, registry


def test_id_is_a_sha256_and_stable() -> None:
    first = requirement_set_id(REQUIREMENTS_DIR, DEFAULT_REGISTRY)
    assert len(first) == 64
    assert first == requirement_set_id(REQUIREMENTS_DIR, DEFAULT_REGISTRY)


def test_identical_copies_have_the_same_id(tmp_path: Path) -> None:
    directory, registry = copy_files(tmp_path)
    assert requirement_set_id(directory, registry) == requirement_set_id(
        REQUIREMENTS_DIR, DEFAULT_REGISTRY
    )


def test_changing_a_rule_file_changes_the_id(tmp_path: Path) -> None:
    directory, registry = copy_files(tmp_path)
    before = requirement_set_id(directory, registry)
    path = directory / "nl.yaml"
    path.write_text(path.read_text(encoding="utf-8") + "\n# edited\n", encoding="utf-8")
    assert requirement_set_id(directory, registry) != before


def test_changing_the_source_registry_changes_the_id(tmp_path: Path) -> None:
    directory, registry = copy_files(tmp_path)
    before = requirement_set_id(directory, registry)
    registry.write_text(registry.read_text(encoding="utf-8") + "\n# edited\n", encoding="utf-8")
    assert requirement_set_id(directory, registry) != before

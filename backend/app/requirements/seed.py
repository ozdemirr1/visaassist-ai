"""Load the requirement files into the database as one versioned requirement set.

The set's id is the SHA-256 of the files that define it (data/requirements/*.yaml and
data/sources.yaml), so loading unchanged files again changes nothing, and every check run can
name exactly which rules it used. The newly loaded set becomes the active one.

Run from backend/ after `uv run alembic upgrade head`:

    uv run python -m app.requirements.seed
"""

import argparse
import hashlib
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app import models
from app.db import get_engine
from app.requirements.loader import REQUIREMENTS_DIR, RequirementData, load_requirement_data
from app.sources.registry import DEFAULT_REGISTRY, REPO_ROOT, Registry, load_registry


def requirement_set_id(requirements_dir: Path, registry_file: Path) -> str:
    """SHA-256 over the names and bytes of every file that defines the requirement set."""
    digest = hashlib.sha256()
    for path in [*sorted(requirements_dir.glob("*.yaml")), registry_file]:
        digest.update(path.name.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def current_git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() or None


@dataclass(frozen=True)
class SeedResult:
    requirement_set_id: str
    created: bool
    requirements: int
    rules: int


def seed(
    session: Session,
    data: RequirementData,
    registry: Registry,
    set_id: str,
    git_commit: str | None = None,
) -> SeedResult:
    """Upsert the sources, insert the requirement set unless it exists, and make it active."""
    for source in registry.sources:
        session.merge(
            models.Source(
                id=source.id,
                title=source.title,
                publisher=source.publisher,
                layer=source.layer,
                destination=source.destination,
                url=str(source.url),
                format=source.format,
                source_date=source.source_date,
                reviewed_on=source.reviewed_on,
            )
        )

    requirements = [r for layer in data.layers for r in layer.requirements]
    rules = [r for layer in data.layers for r in layer.rules]
    created = session.get(models.RequirementSet, set_id) is None
    if created:
        session.add(models.RequirementSet(id=set_id, git_commit=git_commit, active=False))
        # Without ORM relationships the flush order is not derived from foreign keys,
        # so parents are written explicitly before their children.
        session.flush()
        _add_catalog(session, data, set_id)
        _add_items(session, data, set_id)

    session.execute(
        update(models.RequirementSet)
        .where(models.RequirementSet.id != set_id, models.RequirementSet.active)
        .values(active=False)
    )
    session.flush()
    session.execute(
        update(models.RequirementSet).where(models.RequirementSet.id == set_id).values(active=True)
    )
    return SeedResult(set_id, created, len(requirements), len(rules))


def _add_catalog(session: Session, data: RequirementData, set_id: str) -> None:
    catalog = data.catalog
    for type_position, document in enumerate(catalog.document_types):
        session.add(
            models.DocumentType(
                requirement_set_id=set_id,
                id=document.id,
                title_en=document.title.en,
                title_tr=document.title.tr,
                multiple=document.multiple,
                position=type_position,
            )
        )
    session.flush()
    for document in catalog.document_types:
        fields = [(f, False) for f in document.fields] + [(f, True) for f in catalog.common_fields]
        for field_position, (field, common) in enumerate(fields):
            session.add(
                models.DocumentField(
                    requirement_set_id=set_id,
                    document_type_id=document.id,
                    id=field.id,
                    type=field.type,
                    title_en=field.title.en,
                    title_tr=field.title.tr,
                    optional=field.optional,
                    common=common,
                    position=field_position,
                )
            )
    session.flush()


def _add_items(session: Session, data: RequirementData, set_id: str) -> None:
    position = 0
    for layer in data.layers:
        for requirement in layer.requirements:
            session.add(
                models.Requirement(
                    requirement_set_id=set_id,
                    id=requirement.id,
                    layer=layer.layer,
                    destination=layer.destination,
                    document_type_id=requirement.document,
                    profiles=list(requirement.profiles),
                    submit_as=requirement.submit_as,
                    note_en=requirement.note.en if requirement.note else None,
                    note_tr=requirement.note.tr if requirement.note else None,
                    position=position,
                    **_citation(requirement.source),
                )
            )
            position += 1
        for rule in layer.rules:
            session.add(
                models.Rule(
                    requirement_set_id=set_id,
                    id=rule.id,
                    layer=layer.layer,
                    destination=layer.destination,
                    severity=rule.severity,
                    profiles=list(rule.profiles),
                    title_en=rule.title.en,
                    title_tr=rule.title.tr,
                    check=rule.check.model_dump(mode="json"),
                    position=position,
                    **_citation(rule.source),
                )
            )
            position += 1


def _citation(source) -> dict[str, str]:
    return {
        "source_id": source.source_id,
        "section": source.section,
        "passage": source.passage,
        "basis": source.basis,
    }


def active_requirement_set_id(session: Session) -> str | None:
    return session.scalar(select(models.RequirementSet.id).where(models.RequirementSet.active))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Load data/requirements/ into the database.")
    parser.add_argument("--requirements", type=Path, default=REQUIREMENTS_DIR)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    args = parser.parse_args(argv)

    registry = load_registry(args.registry)
    data = load_requirement_data(args.requirements, registry)
    set_id = requirement_set_id(args.requirements, args.registry)

    with Session(get_engine()) as session, session.begin():
        result = seed(session, data, registry, set_id, current_git_commit())

    state = "loaded" if result.created else "already loaded"
    print(
        f"Requirement set {result.requirement_set_id[:12]} {state} and active: "
        f"{result.requirements} requirements, {result.rules} rules."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

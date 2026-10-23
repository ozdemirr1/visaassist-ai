"""Load the requirement files and check every cross-reference before they are used."""

from dataclasses import dataclass
from pathlib import Path

import yaml

from app.requirements.schema import DocumentCatalog, Layer, Profile, Requirement, Rule
from app.sources.registry import REPO_ROOT, Registry, load_registry

REQUIREMENTS_DIR = REPO_ROOT / "data" / "requirements"
CATALOG_FILE = "document-types.yaml"


class RequirementDataError(ValueError):
    """The requirement files are inconsistent; `problems` lists every issue found."""

    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        super().__init__("invalid requirement data:\n- " + "\n- ".join(problems))


@dataclass(frozen=True)
class RuleSet:
    """The EU baseline plus one destination's national layer."""

    destination: str
    requirements: list[Requirement]
    rules: list[Rule]

    def checklist(self, profile: Profile) -> list[Requirement]:
        return [r for r in self.requirements if profile in r.profiles]

    def rules_for(self, profile: Profile) -> list[Rule]:
        return [r for r in self.rules if profile in r.profiles]


@dataclass(frozen=True)
class RequirementData:
    catalog: DocumentCatalog
    layers: list[Layer]

    @property
    def destinations(self) -> list[str]:
        return sorted(layer.destination for layer in self.layers if layer.destination)

    def ruleset(self, destination: str) -> RuleSet:
        eu = [layer for layer in self.layers if layer.layer == "eu"]
        national = [layer for layer in self.layers if layer.destination == destination]
        if not national:
            raise KeyError(destination)
        chosen = eu + national
        return RuleSet(
            destination=destination,
            requirements=[r for layer in chosen for r in layer.requirements],
            rules=[r for layer in chosen for r in layer.rules],
        )


def _read_yaml(path: Path) -> object:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_requirement_data(
    directory: Path = REQUIREMENTS_DIR, registry: Registry | None = None
) -> RequirementData:
    """Parse the catalog and all layers, then validate references across them."""
    catalog = DocumentCatalog.model_validate(_read_yaml(directory / CATALOG_FILE))
    layers = [
        Layer.model_validate(_read_yaml(path))
        for path in sorted(directory.glob("*.yaml"))
        if path.name != CATALOG_FILE
    ]
    data = RequirementData(catalog=catalog, layers=layers)
    problems = find_problems(data, registry or load_registry())
    if problems:
        raise RequirementDataError(problems)
    return data


def find_problems(data: RequirementData, registry: Registry) -> list[str]:
    """Every inconsistency between the layers, the document catalog and the source registry."""
    problems: list[str] = []
    sources = {s.id: s for s in registry.sources}

    eu_layers = [layer for layer in data.layers if layer.layer == "eu"]
    if len(eu_layers) != 1:
        problems.append(f"expected exactly one EU layer, found {len(eu_layers)}")
    national = [layer.destination for layer in data.layers if layer.destination]
    for destination in sorted({d for d in national if national.count(d) > 1}):
        problems.append(f"more than one national layer for {destination}")

    seen: set[str] = set()
    for layer in data.layers:
        for item in [*layer.requirements, *layer.rules]:
            where = f"{item.id}"
            if item.id in seen:
                problems.append(f"{where}: id used more than once")
            seen.add(item.id)
            if not item.id.startswith(f"{layer.id_prefix}-"):
                problems.append(f"{where}: id must start with '{layer.id_prefix}-'")

            source = sources.get(item.source.source_id)
            if source is None:
                problems.append(f"{where}: unknown source '{item.source.source_id}'")
            elif source.destination not in (None, layer.destination):
                problems.append(
                    f"{where}: cites a {source.destination} source in the "
                    f"{layer.destination or 'EU'} layer"
                )

        for requirement in layer.requirements:
            if data.catalog.document(requirement.document) is None:
                problems.append(f"{requirement.id}: unknown document '{requirement.document}'")

        for rule in layer.rules:
            problems.extend(_check_rule_fields(rule, data.catalog))

    for destination in data.destinations:
        problems.extend(_check_rules_have_documents(data.ruleset(destination)))
    return problems


def _check_rule_fields(rule: Rule, catalog: DocumentCatalog) -> list[str]:
    problems = []
    for document_id, field_id, allowed in rule.check.field_refs():
        document = catalog.document(document_id)
        if document is None:
            problems.append(f"{rule.id}: unknown document '{document_id}'")
            continue
        field = catalog.field(document_id, field_id)
        if field is None:
            problems.append(f"{rule.id}: {document_id} has no field '{field_id}'")
        elif field.type not in allowed:
            problems.append(
                f"{rule.id}: {document_id}.{field_id} is {field.type}, "
                f"{rule.check.kind} needs {' or '.join(allowed)}"
            )
    if rule.check.kind == "recent_monthly_count":
        document = catalog.document(rule.check.document)
        if document is not None and not document.multiple:
            problems.append(f"{rule.id}: {document.id} must allow multiple documents")
    return problems


def _check_rules_have_documents(ruleset: RuleSet) -> list[str]:
    """A rule that reads a document no checklist item asks for would never run."""
    problems = []
    for profile in ("employed", "student"):
        required = {r.document for r in ruleset.checklist(profile)}
        for rule in ruleset.rules_for(profile):
            documents = list(dict.fromkeys(d for d, _, _ in rule.check.field_refs()))
            if not documents:
                continue
            if rule.check.kind in ("names_match", "values_match"):
                # compared documents are checked when present; the reference must be asked for
                missing = [documents[0]] if documents[0] not in required else []
            elif rule.check.kind in ("max_age", "field_true"):
                # the rule runs on whichever of its documents the checklist asks for
                missing = [] if required.intersection(documents) else documents
            else:
                missing = [d for d in documents if d not in required]
            problems.extend(
                f"{rule.id}: {ruleset.destination}/{profile} checklist does not ask for '{d}'"
                for d in missing
            )
    return sorted(set(problems))

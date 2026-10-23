"""Schema of the requirement files in `data/requirements/` (FR-02, FR-09, FR-10).

A destination's rule set is the EU baseline plus that destination's national layer. Every
requirement (checklist item) and every rule cites an official source from `data/sources.yaml`.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Id = Annotated[str, Field(pattern=r"^[a-z0-9]+([-_][a-z0-9]+)*$")]
LanguageCode = Annotated[str, Field(pattern=r"^[a-z]{2}$")]
Profile = Literal["employed", "student"]
ALL_PROFILES: list[Profile] = ["employed", "student"]
FieldType = Literal["text", "date", "int", "bool", "money", "language"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LocalizedText(Strict):
    """Interface text in both languages (NFR-10)."""

    en: str = Field(min_length=1)
    tr: str = Field(min_length=1)


# Documents


class FieldDef(Strict):
    id: Id
    type: FieldType
    title: LocalizedText
    optional: bool = False


class DocumentType(Strict):
    id: Id
    title: LocalizedText
    fields: list[FieldDef] = Field(min_length=1)
    multiple: bool = False  # the applicant uploads several documents of this type


class DocumentCatalog(Strict):
    common_fields: list[FieldDef]
    document_types: list[DocumentType] = Field(min_length=1)

    @model_validator(mode="after")
    def ids_are_unique(self) -> "DocumentCatalog":
        _raise_on_duplicates("document type", [d.id for d in self.document_types])
        for document in self.document_types:
            ids = [f.id for f in self.common_fields] + [f.id for f in document.fields]
            _raise_on_duplicates(f"field of {document.id}", ids)
        return self

    def document(self, document_id: str) -> DocumentType | None:
        return next((d for d in self.document_types if d.id == document_id), None)

    def field(self, document_id: str, field_id: str) -> FieldDef | None:
        document = self.document(document_id)
        if document is None:
            return None
        return next((f for f in self.common_fields + document.fields if f.id == field_id), None)


# Sources


class Citation(Strict):
    source_id: Id
    section: str = Field(min_length=1)
    passage: str = Field(min_length=1)
    # "stated": the source says it; "derived": follows from what it says (passage explains how)
    basis: Literal["stated", "derived"] = "stated"


# Checks: each kind names the document fields it reads and the field types it needs.

FieldRef = tuple[str, str, tuple[FieldType, ...]]  # (document, field, allowed types)


class MaxAge(Strict):
    kind: Literal["max_age"]
    documents: list[Id] = Field(min_length=1)
    field: Id
    amount: int = Field(gt=0)
    unit: Literal["months", "years"]

    def field_refs(self) -> list[FieldRef]:
        return [(d, self.field, ("date",)) for d in self.documents]


class ValidAfterTrip(Strict):
    kind: Literal["valid_after_trip"]
    document: Id
    field: Id
    months: int = Field(gt=0)

    def field_refs(self) -> list[FieldRef]:
        return [(self.document, self.field, ("date",))]


class MinValue(Strict):
    kind: Literal["min_value"]
    document: Id
    field: Id
    value: int

    def field_refs(self) -> list[FieldRef]:
        return [(self.document, self.field, ("int",))]


class MinAmount(Strict):
    kind: Literal["min_amount"]
    document: Id
    field: Id
    amount: float = Field(gt=0)
    currency: str = Field(pattern=r"^[A-Z]{3}$")

    def field_refs(self) -> list[FieldRef]:
        return [(self.document, self.field, ("money",))]


class FieldTrue(Strict):
    kind: Literal["field_true"]
    documents: list[Id] = Field(min_length=1)
    fields: list[Id] = Field(min_length=1)

    def field_refs(self) -> list[FieldRef]:
        return [(d, f, ("bool",)) for d in self.documents for f in self.fields]


class FieldsPresent(Strict):
    kind: Literal["fields_present"]
    document: Id
    fields: list[Id] = Field(min_length=1)

    def field_refs(self) -> list[FieldRef]:
        any_type: tuple[FieldType, ...] = ("text", "date", "int", "bool", "money", "language")
        return [(self.document, f, any_type) for f in self.fields]


class PeriodCoversTrip(Strict):
    kind: Literal["period_covers_trip"]
    document: Id
    start_field: Id
    end_field: Id

    def field_refs(self) -> list[FieldRef]:
        return [(self.document, f, ("date",)) for f in (self.start_field, self.end_field)]


class CoversRecentMonths(Strict):
    kind: Literal["covers_recent_months"]
    document: Id
    start_field: Id
    end_field: Id
    months: int = Field(gt=0)

    def field_refs(self) -> list[FieldRef]:
        return [(self.document, f, ("date",)) for f in (self.start_field, self.end_field)]


class RecentMonthlyCount(Strict):
    kind: Literal["recent_monthly_count"]
    document: Id
    date_field: Id
    months: int = Field(gt=0)

    def field_refs(self) -> list[FieldRef]:
        return [(self.document, self.date_field, ("date",))]


class _CrossDocument(Strict):
    reference: str = Field(pattern=r"^[a-z0-9_]+\.[a-z0-9_]+$")
    compare: list[Annotated[str, Field(pattern=r"^[a-z0-9_]+\.[a-z0-9_]+$")]] = Field(min_length=1)

    def field_refs(self) -> list[FieldRef]:
        refs = [self.reference, *self.compare]
        return [(r.split(".")[0], r.split(".")[1], ("text",)) for r in refs]


class NamesMatch(_CrossDocument):
    kind: Literal["names_match"]


class ValuesMatch(_CrossDocument):
    kind: Literal["values_match"]


class TranslationPresent(Strict):
    """Every document not written in one of `languages` has a translation into one of them."""

    kind: Literal["translation_present"]
    languages: list[LanguageCode] = Field(min_length=1)

    def field_refs(self) -> list[FieldRef]:
        return []  # uses the common fields `language` and `translation_language`


Check = Annotated[
    MaxAge
    | ValidAfterTrip
    | MinValue
    | MinAmount
    | FieldTrue
    | FieldsPresent
    | PeriodCoversTrip
    | CoversRecentMonths
    | RecentMonthlyCount
    | NamesMatch
    | ValuesMatch
    | TranslationPresent,
    Field(discriminator="kind"),
]


# Layers


class Requirement(Strict):
    """A checklist item: one document the applicant submits."""

    id: Id
    document: Id
    profiles: list[Profile] = Field(default_factory=lambda: list(ALL_PROFILES), min_length=1)
    submit_as: Literal["original", "copy", "original_and_copy"]
    note: LocalizedText | None = None
    source: Citation


class Rule(Strict):
    id: Id
    title: LocalizedText
    severity: Literal["error", "warning"]
    profiles: list[Profile] = Field(default_factory=lambda: list(ALL_PROFILES), min_length=1)
    check: Check
    source: Citation


class Layer(Strict):
    layer: Literal["eu", "national"]
    destination: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    visa: Literal["schengen-c"]
    purposes: list[Literal["tourism"]] = Field(min_length=1)
    requirements: list[Requirement] = Field(default_factory=list)
    rules: list[Rule] = Field(default_factory=list)

    @model_validator(mode="after")
    def destination_matches_layer(self) -> "Layer":
        if (self.layer == "national") != (self.destination is not None):
            raise ValueError("a national layer needs a destination; the EU layer has none")
        return self

    @property
    def id_prefix(self) -> str:
        return "eu" if self.destination is None else self.destination.lower()


def _raise_on_duplicates(what: str, ids: list[str]) -> None:
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise ValueError(f"duplicate {what} ids: {', '.join(duplicates)}")

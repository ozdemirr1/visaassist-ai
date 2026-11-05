"""Database tables (SQLAlchemy 2). Design: docs/design/data-model.md.

Week 7 creates the requirement tables: official sources and versioned requirement sets with
their document types, checklist items and rules. Application files, documents and findings
follow in week 9.
"""

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Source(Base):
    """An official page or document requirements are taken from (data/sources.yaml)."""

    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    title: Mapped[str] = mapped_column(Text)
    publisher: Mapped[str] = mapped_column(Text)
    layer: Mapped[str] = mapped_column(String(16))
    destination: Mapped[str | None] = mapped_column(String(2))
    url: Mapped[str] = mapped_column(Text)
    format: Mapped[str] = mapped_column(String(8))
    source_date: Mapped[date | None] = mapped_column(Date)
    reviewed_on: Mapped[date] = mapped_column(Date)


class RequirementSet(Base):
    """One loaded version of data/requirements/, identified by the hash of its files."""

    __tablename__ = "requirement_sets"
    __table_args__ = (
        # At most one active set at a time.
        Index(
            "uq_requirement_sets_one_active",
            "active",
            unique=True,
            postgresql_where=text("active"),
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    git_commit: Mapped[str | None] = mapped_column(String(40))
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    active: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))


class DocumentType(Base):
    """A document type and its titles, versioned with the requirement set."""

    __tablename__ = "document_types"

    requirement_set_id: Mapped[str] = mapped_column(
        ForeignKey("requirement_sets.id", ondelete="CASCADE"), primary_key=True
    )
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    title_en: Mapped[str] = mapped_column(Text)
    title_tr: Mapped[str] = mapped_column(Text)
    multiple: Mapped[bool] = mapped_column(Boolean)
    position: Mapped[int] = mapped_column(Integer)


class DocumentField(Base):
    """A field the applicant enters for a document type (common fields are repeated per type)."""

    __tablename__ = "document_fields"
    __table_args__ = (
        ForeignKeyConstraint(
            ["requirement_set_id", "document_type_id"],
            ["document_types.requirement_set_id", "document_types.id"],
            ondelete="CASCADE",
        ),
    )

    requirement_set_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    document_type_id: Mapped[str] = mapped_column(Text, primary_key=True)
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    type: Mapped[str] = mapped_column(String(16))
    title_en: Mapped[str] = mapped_column(Text)
    title_tr: Mapped[str] = mapped_column(Text)
    optional: Mapped[bool] = mapped_column(Boolean)
    common: Mapped[bool] = mapped_column(Boolean)
    position: Mapped[int] = mapped_column(Integer)


class _Cited:
    """Columns every requirement and rule carries: the source it cites."""

    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"))
    section: Mapped[str] = mapped_column(Text)
    passage: Mapped[str] = mapped_column(Text)
    basis: Mapped[str] = mapped_column(String(8))


class Requirement(_Cited, Base):
    """A checklist item: one document, for some profiles, in one layer."""

    __tablename__ = "requirements"
    __table_args__ = (
        ForeignKeyConstraint(
            ["requirement_set_id", "document_type_id"],
            ["document_types.requirement_set_id", "document_types.id"],
            ondelete="CASCADE",
        ),
    )

    requirement_set_id: Mapped[str] = mapped_column(
        ForeignKey("requirement_sets.id", ondelete="CASCADE"), primary_key=True
    )
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    layer: Mapped[str] = mapped_column(String(16))
    destination: Mapped[str | None] = mapped_column(String(2))
    document_type_id: Mapped[str] = mapped_column(Text)
    profiles: Mapped[list[str]] = mapped_column(ARRAY(Text))
    submit_as: Mapped[str] = mapped_column(String(24))
    note_en: Mapped[str | None] = mapped_column(Text)
    note_tr: Mapped[str | None] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer)


class Rule(_Cited, Base):
    """A check on entered fields; `check` holds the validated Check model as JSON."""

    __tablename__ = "rules"

    requirement_set_id: Mapped[str] = mapped_column(
        ForeignKey("requirement_sets.id", ondelete="CASCADE"), primary_key=True
    )
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    layer: Mapped[str] = mapped_column(String(16))
    destination: Mapped[str | None] = mapped_column(String(2))
    severity: Mapped[str] = mapped_column(String(8))
    profiles: Mapped[list[str]] = mapped_column(ARRAY(Text))
    title_en: Mapped[str] = mapped_column(Text)
    title_tr: Mapped[str] = mapped_column(Text)
    check: Mapped[dict] = mapped_column(JSONB)
    position: Mapped[int] = mapped_column(Integer)

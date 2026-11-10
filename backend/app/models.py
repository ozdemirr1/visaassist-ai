"""Database tables (SQLAlchemy 2). Design: docs/design/data-model.md.

Week 7 created the requirement tables: official sources and versioned requirement sets with
their document types, checklist items and rules. Week 9 adds accounts and sessions (ADR 0004),
application files, consents and encrypted documents (ADR 0005); findings follow.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
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
from sqlalchemy.dialects.postgresql import ARRAY, BYTEA, JSONB, UUID
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


class User(Base):
    """An account: an applicant or an administrator (FR-04)."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(Text, unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(16), default="applicant")
    language: Mapped[str] = mapped_column(String(2), default="tr")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuthSession(Base):
    """A login session. Only the SHA-256 of the cookie token is stored (ADR 0004)."""

    __tablename__ = "sessions"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class LoginAttempt(Base):
    """One login attempt, counted per e-mail and per IP address to slow down guessing."""

    __tablename__ = "login_attempts"
    __table_args__ = (
        Index("ix_login_attempts_email_time", "email", "attempted_at"),
        Index("ix_login_attempts_ip_time", "ip_address", "attempted_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(Text)
    ip_address: Mapped[str] = mapped_column(Text)
    succeeded: Mapped[bool] = mapped_column(Boolean)
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ApplicationFile(Base):
    """One planned visa application of a user (FR-05), tied to the requirement set it uses."""

    __tablename__ = "application_files"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    destination: Mapped[str] = mapped_column(String(2))
    visa: Mapped[str] = mapped_column(String(16), default="schengen-c")
    purpose: Mapped[str] = mapped_column(String(16), default="tourism")
    profile: Mapped[str] = mapped_column(String(16))
    trip_start: Mapped[date] = mapped_column(Date)
    trip_end: Mapped[date] = mapped_column(Date)
    application_date: Mapped[date] = mapped_column(Date)
    step: Mapped[str] = mapped_column(String(16), default="draft")
    requirement_set_id: Mapped[str] = mapped_column(ForeignKey("requirement_sets.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("trip_end >= trip_start", name="ck_application_files_trip_dates"),
    )


class ApplicationEvent(Base):
    """A step the application file reached (FR-06): appointment, documents, submitted, decided."""

    __tablename__ = "application_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_file_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("application_files.id", ondelete="CASCADE"), index=True
    )
    step: Mapped[str] = mapped_column(String(16))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Consent(Base):
    """Consent to document processing, per version of the consent text (NFR-01, ADR 0005)."""

    __tablename__ = "consents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[str] = mapped_column(String(32))
    given_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Document(Base):
    """An uploaded document; the file itself is encrypted on the storage volume (ADR 0005)."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_file_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("application_files.id", ondelete="CASCADE"), index=True
    )
    requirement_id: Mapped[str] = mapped_column(Text)
    document_type_id: Mapped[str] = mapped_column(Text)
    storage_key: Mapped[str] = mapped_column(String(32), unique=True)
    wrapped_key: Mapped[bytes] = mapped_column(BYTEA)
    key_id: Mapped[str] = mapped_column(String(16))
    original_name_encrypted: Mapped[bytes] = mapped_column(BYTEA)
    mime_type: Mapped[str] = mapped_column(String(32))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    language: Mapped[str | None] = mapped_column(String(2))
    translation_language: Mapped[str | None] = mapped_column(String(2))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    delete_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

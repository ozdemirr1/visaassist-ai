"""Consents and encrypted documents (FR-07, FR-11, NFR-01, ADR 0005).

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "consents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column("given_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_consents_user_id", "consents", ["user_id"])
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "application_file_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("application_files.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("requirement_id", sa.Text(), nullable=False),
        sa.Column("document_type_id", sa.Text(), nullable=False),
        sa.Column("storage_key", sa.String(32), nullable=False, unique=True),
        sa.Column("wrapped_key", postgresql.BYTEA(), nullable=False),
        sa.Column("key_id", sa.String(16), nullable=False),
        sa.Column("original_name_encrypted", postgresql.BYTEA(), nullable=False),
        sa.Column("mime_type", sa.String(32), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("language", sa.String(2)),
        sa.Column("translation_language", sa.String(2)),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delete_after", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_documents_application_file_id", "documents", ["application_file_id"])
    op.create_index("ix_documents_delete_after", "documents", ["delete_after"])


def downgrade() -> None:
    op.drop_index("ix_documents_delete_after", table_name="documents")
    op.drop_index("ix_documents_application_file_id", table_name="documents")
    op.drop_table("documents")
    op.drop_index("ix_consents_user_id", table_name="consents")
    op.drop_table("consents")

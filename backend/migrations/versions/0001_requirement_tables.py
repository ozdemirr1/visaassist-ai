"""Requirement tables: sources, requirement sets, document types and fields, requirements, rules.

Revision ID: 0001
Revises:
Create Date: 2026-11-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _cited_columns() -> list[sa.Column]:
    return [
        sa.Column("source_id", sa.Text(), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("section", sa.Text(), nullable=False),
        sa.Column("passage", sa.Text(), nullable=False),
        sa.Column("basis", sa.String(8), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("publisher", sa.Text(), nullable=False),
        sa.Column("layer", sa.String(16), nullable=False),
        sa.Column("destination", sa.String(2)),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("format", sa.String(8), nullable=False),
        sa.Column("source_date", sa.Date()),
        sa.Column("reviewed_on", sa.Date(), nullable=False),
    )
    op.create_table(
        "requirement_sets",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("git_commit", sa.String(40)),
        sa.Column(
            "loaded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("active", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.create_index(
        "uq_requirement_sets_one_active",
        "requirement_sets",
        ["active"],
        unique=True,
        postgresql_where=sa.text("active"),
    )
    op.create_table(
        "document_types",
        sa.Column(
            "requirement_set_id",
            sa.String(64),
            sa.ForeignKey("requirement_sets.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("title_en", sa.Text(), nullable=False),
        sa.Column("title_tr", sa.Text(), nullable=False),
        sa.Column("multiple", sa.Boolean(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
    )
    op.create_table(
        "document_fields",
        sa.Column("requirement_set_id", sa.String(64), primary_key=True),
        sa.Column("document_type_id", sa.Text(), primary_key=True),
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("type", sa.String(16), nullable=False),
        sa.Column("title_en", sa.Text(), nullable=False),
        sa.Column("title_tr", sa.Text(), nullable=False),
        sa.Column("optional", sa.Boolean(), nullable=False),
        sa.Column("common", sa.Boolean(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["requirement_set_id", "document_type_id"],
            ["document_types.requirement_set_id", "document_types.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_table(
        "requirements",
        sa.Column(
            "requirement_set_id",
            sa.String(64),
            sa.ForeignKey("requirement_sets.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("layer", sa.String(16), nullable=False),
        sa.Column("destination", sa.String(2)),
        sa.Column("document_type_id", sa.Text(), nullable=False),
        sa.Column("profiles", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("submit_as", sa.String(24), nullable=False),
        sa.Column("note_en", sa.Text()),
        sa.Column("note_tr", sa.Text()),
        sa.Column("position", sa.Integer(), nullable=False),
        *_cited_columns(),
        sa.ForeignKeyConstraint(
            ["requirement_set_id", "document_type_id"],
            ["document_types.requirement_set_id", "document_types.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_table(
        "rules",
        sa.Column(
            "requirement_set_id",
            sa.String(64),
            sa.ForeignKey("requirement_sets.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("layer", sa.String(16), nullable=False),
        sa.Column("destination", sa.String(2)),
        sa.Column("severity", sa.String(8), nullable=False),
        sa.Column("profiles", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("title_en", sa.Text(), nullable=False),
        sa.Column("title_tr", sa.Text(), nullable=False),
        sa.Column("check", postgresql.JSONB(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        *_cited_columns(),
    )


def downgrade() -> None:
    op.drop_table("rules")
    op.drop_table("requirements")
    op.drop_table("document_fields")
    op.drop_table("document_types")
    op.drop_index("uq_requirement_sets_one_active", table_name="requirement_sets")
    op.drop_table("requirement_sets")
    op.drop_table("sources")

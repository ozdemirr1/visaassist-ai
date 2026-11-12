"""Stored check runs, without the compared values (FR-09, FR-10, ADR 0005).

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "check_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "application_file_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("application_files.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "requirement_set_id",
            sa.String(64),
            sa.ForeignKey("requirement_sets.id"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("missing_documents", postgresql.ARRAY(sa.Text), nullable=False),
        sa.Column("results", postgresql.JSONB, nullable=False),
        sa.Column("summary", postgresql.JSONB, nullable=False),
    )
    op.create_index("ix_check_runs_application_file_id", "check_runs", ["application_file_id"])


def downgrade() -> None:
    op.drop_index("ix_check_runs_application_file_id", table_name="check_runs")
    op.drop_table("check_runs")

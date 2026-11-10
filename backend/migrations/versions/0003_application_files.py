"""Application files and their step events (FR-05, FR-06).

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "application_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("destination", sa.String(2), nullable=False),
        sa.Column("visa", sa.String(16), nullable=False),
        sa.Column("purpose", sa.String(16), nullable=False),
        sa.Column("profile", sa.String(16), nullable=False),
        sa.Column("trip_start", sa.Date(), nullable=False),
        sa.Column("trip_end", sa.Date(), nullable=False),
        sa.Column("application_date", sa.Date(), nullable=False),
        sa.Column("step", sa.String(16), nullable=False),
        sa.Column(
            "requirement_set_id",
            sa.String(64),
            sa.ForeignKey("requirement_sets.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("trip_end >= trip_start", name="ck_application_files_trip_dates"),
    )
    op.create_index("ix_application_files_user_id", "application_files", ["user_id"])
    op.create_table(
        "application_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "application_file_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("application_files.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("step", sa.String(16), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_application_events_application_file_id", "application_events", ["application_file_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_application_events_application_file_id", table_name="application_events")
    op.drop_table("application_events")
    op.drop_index("ix_application_files_user_id", table_name="application_files")
    op.drop_table("application_files")

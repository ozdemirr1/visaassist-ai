"""Log of language-model calls with tokens and cost (NFR-06, ADR 0007).

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "model_calls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("purpose", sa.String(32), nullable=False),
        sa.Column("document_type_id", sa.Text, nullable=True),
        sa.Column("model", sa.Text, nullable=False),
        sa.Column("prompt_version", sa.String(32), nullable=False),
        sa.Column("input_tokens", sa.Integer, nullable=False),
        sa.Column("output_tokens", sa.Integer, nullable=False),
        sa.Column("cost_usd", sa.Float, nullable=True),
        sa.Column("seconds", sa.Float, nullable=False),
        sa.Column("succeeded", sa.Boolean, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_model_calls_user_id", "model_calls", ["user_id"])
    op.create_index("ix_model_calls_created_at", "model_calls", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_model_calls_created_at", table_name="model_calls")
    op.drop_index("ix_model_calls_user_id", table_name="model_calls")
    op.drop_table("model_calls")

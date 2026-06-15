"""widen language columns from String(10) to String(50)

The ORM models define language as String(50) but migration 001 created
them as String(10). Values longer than 10 chars (e.g. "Runyankore")
would be silently truncated on a production DB built via Alembic.

Revision ID: 003
Revises: 002
Create Date: 2026-06-15
"""

import sqlalchemy as sa
from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("calls") as batch_op:
        batch_op.alter_column(
            "language",
            existing_type=sa.String(10),
            type_=sa.String(50),
            existing_nullable=True,
        )

    with op.batch_alter_table("caller_preferences") as batch_op:
        batch_op.alter_column(
            "language",
            existing_type=sa.String(10),
            type_=sa.String(50),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("caller_preferences") as batch_op:
        batch_op.alter_column(
            "language",
            existing_type=sa.String(50),
            type_=sa.String(10),
            existing_nullable=False,
        )

    with op.batch_alter_table("calls") as batch_op:
        batch_op.alter_column(
            "language",
            existing_type=sa.String(50),
            type_=sa.String(10),
            existing_nullable=True,
        )

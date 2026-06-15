"""move timing and audio URL to call_metrics; drop extension_registry

Revision ID: 002
Revises: 001
Create Date: 2026-06-11
"""

from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "call_metrics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("call_id", sa.String(255), nullable=False),
        sa.Column("question_number", sa.Integer(), nullable=False),
        sa.Column("audio_url", sa.String(2000), nullable=True),
        sa.Column("stt_duration", sa.Float(), nullable=True),
        sa.Column("agent_duration", sa.Float(), nullable=True),
        sa.Column("tts_duration", sa.Float(), nullable=True),
        sa.Column("total_duration", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("call_id", "question_number", name="uq_call_metrics_call_question"),
    )
    op.create_index("ix_call_metrics_id", "call_metrics", ["id"])
    op.create_index("ix_call_metrics_call_id", "call_metrics", ["call_id"])

    for col in (
        "q1_output_audio_url", "q1_stt_duration", "q1_agent_duration",
        "q1_tts_duration", "q1_total_duration",
        "q2_output_audio_url", "q2_stt_duration", "q2_agent_duration",
        "q2_tts_duration", "q2_total_duration",
    ):
        op.drop_column("calls", col)

    op.drop_table("extension_registry")


def downgrade() -> None:
    op.create_table(
        "extension_registry",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=True),
        sa.Column("extension", sa.String(20), nullable=True),
        sa.Column("name", sa.String(100), nullable=True),
        sa.Column("context", sa.String(100), nullable=True),
        sa.Column("registered", sa.Boolean(), nullable=True),
        sa.Column("last_ip", sa.String(45), nullable=True),
        sa.Column("last_port", sa.Integer(), nullable=True),
        sa.Column("last_contact_time", sa.DateTime(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("auth_username", sa.String(100), nullable=True),
        sa.Column("auth_realm", sa.String(100), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("extension"),
    )

    for col, type_ in (
        ("q1_output_audio_url", sa.String(2000)),
        ("q1_stt_duration", sa.Float()),
        ("q1_agent_duration", sa.Float()),
        ("q1_tts_duration", sa.Float()),
        ("q1_total_duration", sa.Float()),
        ("q2_output_audio_url", sa.String(2000)),
        ("q2_stt_duration", sa.Float()),
        ("q2_agent_duration", sa.Float()),
        ("q2_tts_duration", sa.Float()),
        ("q2_total_duration", sa.Float()),
    ):
        op.add_column("calls", sa.Column(col, type_, nullable=True))

    op.drop_index("ix_call_metrics_call_id", "call_metrics")
    op.drop_index("ix_call_metrics_id", "call_metrics")
    op.drop_table("call_metrics")

"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-05-26
"""

from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "calls",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=True),
        sa.Column("call_id", sa.String(255), nullable=False),
        sa.Column("caller_id", sa.String(50), nullable=True),
        sa.Column("extension", sa.String(20), nullable=True),
        sa.Column("language", sa.String(10), nullable=True),
        sa.Column("speaker_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(50), nullable=True),
        sa.Column("q1_input_text", sa.Text(), nullable=True),
        sa.Column("q1_output_text", sa.Text(), nullable=True),
        sa.Column("q1_detected_language", sa.String(20), nullable=True),
        sa.Column("q1_input_audio", sa.String(500), nullable=True),
        sa.Column("q1_output_audio_url", sa.String(2000), nullable=True),
        sa.Column("q1_stt_duration", sa.Float(), nullable=True),
        sa.Column("q1_agent_duration", sa.Float(), nullable=True),
        sa.Column("q1_tts_duration", sa.Float(), nullable=True),
        sa.Column("q1_total_duration", sa.Float(), nullable=True),
        sa.Column("q2_input_text", sa.Text(), nullable=True),
        sa.Column("q2_output_text", sa.Text(), nullable=True),
        sa.Column("q2_detected_language", sa.String(20), nullable=True),
        sa.Column("q2_input_audio", sa.String(500), nullable=True),
        sa.Column("q2_output_audio_url", sa.String(2000), nullable=True),
        sa.Column("q2_stt_duration", sa.Float(), nullable=True),
        sa.Column("q2_agent_duration", sa.Float(), nullable=True),
        sa.Column("q2_tts_duration", sa.Float(), nullable=True),
        sa.Column("q2_total_duration", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("call_id"),
    )
    op.create_index("ix_calls_id", "calls", ["id"])
    op.create_index("ix_calls_call_id", "calls", ["call_id"])
    op.create_index("ix_calls_caller_id", "calls", ["caller_id"])
    op.create_index("ix_calls_extension", "calls", ["extension"])
    op.create_index("ix_calls_status", "calls", ["status"])
    op.create_index("ix_calls_timestamp", "calls", ["timestamp"])

    op.create_table(
        "caller_preferences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("caller_id", sa.String(50), nullable=False),
        sa.Column("language", sa.String(10), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("caller_id"),
    )
    op.create_index("ix_caller_preferences_id", "caller_preferences", ["id"])
    op.create_index("ix_caller_preferences_caller_id", "caller_preferences", ["caller_id"])

    op.create_table(
        "asterisk_cdr",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=True),
        sa.Column("uniqueid", sa.String(255), nullable=True),
        sa.Column("call_id", sa.String(255), nullable=True),
        sa.Column("src", sa.String(50), nullable=True),
        sa.Column("dst", sa.String(50), nullable=True),
        sa.Column("channel", sa.String(255), nullable=True),
        sa.Column("context", sa.String(100), nullable=True),
        sa.Column("exten", sa.String(50), nullable=True),
        sa.Column("calldate", sa.DateTime(), nullable=True),
        sa.Column("start_time", sa.DateTime(), nullable=True),
        sa.Column("answer_time", sa.DateTime(), nullable=True),
        sa.Column("end_time", sa.DateTime(), nullable=True),
        sa.Column("duration", sa.Integer(), nullable=True),
        sa.Column("billsec", sa.Integer(), nullable=True),
        sa.Column("disposition", sa.String(50), nullable=True),
        sa.Column("cause", sa.String(50), nullable=True),
        sa.Column("cause_txt", sa.String(255), nullable=True),
        sa.Column("recording_file", sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uniqueid"),
    )
    op.create_index("ix_asterisk_cdr_id", "asterisk_cdr", ["id"])
    op.create_index("ix_asterisk_cdr_uniqueid", "asterisk_cdr", ["uniqueid"])
    op.create_index("ix_asterisk_cdr_call_id", "asterisk_cdr", ["call_id"])
    op.create_index("ix_asterisk_cdr_src", "asterisk_cdr", ["src"])
    op.create_index("ix_asterisk_cdr_dst", "asterisk_cdr", ["dst"])
    op.create_index("ix_asterisk_cdr_exten", "asterisk_cdr", ["exten"])
    op.create_index("ix_asterisk_cdr_calldate", "asterisk_cdr", ["calldate"])
    op.create_index("ix_asterisk_cdr_disposition", "asterisk_cdr", ["disposition"])
    op.create_index("ix_asterisk_cdr_timestamp", "asterisk_cdr", ["timestamp"])

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
    op.create_index("ix_extension_registry_id", "extension_registry", ["id"])
    op.create_index("ix_extension_registry_extension", "extension_registry", ["extension"])

    op.create_table(
        "system_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=True),
        sa.Column("level", sa.String(20), nullable=True),
        sa.Column("component", sa.String(50), nullable=True),
        sa.Column("event_type", sa.String(100), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("call_id", sa.String(255), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_system_log_id", "system_log", ["id"])
    op.create_index("ix_system_log_timestamp", "system_log", ["timestamp"])
    op.create_index("ix_system_log_level", "system_log", ["level"])
    op.create_index("ix_system_log_component", "system_log", ["component"])
    op.create_index("ix_system_log_event_type", "system_log", ["event_type"])
    op.create_index("ix_system_log_call_id", "system_log", ["call_id"])


def downgrade() -> None:
    op.drop_table("system_log")
    op.drop_table("extension_registry")
    op.drop_table("asterisk_cdr")
    op.drop_table("caller_preferences")
    op.drop_table("calls")

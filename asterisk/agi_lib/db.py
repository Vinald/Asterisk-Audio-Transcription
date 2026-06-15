"""Database operations used by AGI scripts."""

import sys
from datetime import datetime

import pymysql

from .config import DB_CONFIG


def connect() -> pymysql.connections.Connection:
    return pymysql.connect(**DB_CONFIG, autocommit=False)


# ── calls table ───────────────────────────────────────────────────────────────

def insert_call_q1(
    call_id, caller_id, extension, language, speaker_id, status,
    input_text, output_text, detected_language, input_audio,
) -> bool:
    try:
        conn = connect()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO calls
                    (call_id, caller_id, extension, language, speaker_id, status, timestamp,
                     q1_input_text, q1_output_text, q1_detected_language, q1_input_audio)
                VALUES (%s,%s,%s,%s,%s,%s,NOW(),%s,%s,%s,%s)
                """,
                (
                    call_id, caller_id, extension, language, speaker_id, status,
                    input_text or None, output_text or None, detected_language, input_audio,
                ),
            )
        conn.commit()
        return True
    except pymysql.err.IntegrityError as e:
        sys.stderr.write(f"DB integrity error (Q1 insert): {e}\n")
        return False
    except Exception as e:
        sys.stderr.write(f"DB error (Q1 insert): {e}\n")
        return False
    finally:
        conn.close()


def update_call_q2(
    call_id,
    input_text, output_text, detected_language, input_audio,
) -> bool:
    try:
        conn = connect()
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE calls SET
                    q2_input_text=%s, q2_output_text=%s, q2_detected_language=%s,
                    q2_input_audio=%s, status='completed'
                WHERE call_id=%s
                """,
                (
                    input_text or None, output_text or None, detected_language,
                    input_audio, call_id,
                ),
            )
        conn.commit()
        return True
    except Exception as e:
        sys.stderr.write(f"DB error (Q2 update): {e}\n")
        return False
    finally:
        conn.close()


# ── call_metrics table ────────────────────────────────────────────────────────

def insert_call_metrics(
    call_id, question_number, audio_url,
    stt_duration, agent_duration, tts_duration, total_duration,
) -> None:
    try:
        conn = connect()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO call_metrics
                    (call_id, question_number, audio_url,
                     stt_duration, agent_duration, tts_duration, total_duration)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                """,
                (call_id, question_number, audio_url or None,
                 stt_duration, agent_duration, tts_duration, total_duration),
            )
        conn.commit()
    except Exception as e:
        sys.stderr.write(f"DB error (call_metrics insert): {e}\n")
    finally:
        conn.close()


def update_call_status(call_id: str, status: str) -> None:
    try:
        conn = connect()
        with conn.cursor() as cur:
            cur.execute("UPDATE calls SET status=%s WHERE call_id=%s", (status, call_id))
        conn.commit()
    except Exception as e:
        sys.stderr.write(f"DB error (status update): {e}\n")
    finally:
        conn.close()


def insert_error_call(
    call_id, question_number, caller_id, extension,
) -> None:
    status = f"error_q{question_number}"
    if question_number == 1:
        insert_call_q1(
            call_id=call_id, caller_id=caller_id, extension=extension,
            language=None, speaker_id=None, status=status,
            input_text=None, output_text=None, detected_language=None,
            input_audio=None,
        )
    else:
        update_call_q2(
            call_id=call_id,
            input_text=None, output_text=None, detected_language=None,
            input_audio=None,
        )
        update_call_status(call_id, status)


def insert_no_question_call(
    call_id: str, caller_id: str, extension: str, language: str, status: str = "no_question",
) -> bool:
    """Write a minimal calls row for callers who declined to ask a question."""
    return insert_call_q1(
        call_id=call_id, caller_id=caller_id, extension=extension,
        language=language, speaker_id=None, status=status,
        input_text=None, output_text=None, detected_language=None,
        input_audio=None,
    )


# ── asterisk_cdr table ────────────────────────────────────────────────────────

def insert_cdr(
    uniqueid, caller_id, extension, start_dt: datetime, end_dt: datetime,
    disposition: str = "ANSWERED",
) -> None:
    try:
        duration = int((end_dt - start_dt).total_seconds())
        conn = connect()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT IGNORE INTO asterisk_cdr
                    (uniqueid, call_id, src, dst, context, exten, calldate,
                     start_time, end_time, duration, billsec, disposition)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    uniqueid, uniqueid, caller_id, extension, "ivr", extension,
                    start_dt, start_dt, end_dt, duration, duration, disposition,
                ),
            )
        conn.commit()
    except Exception as e:
        sys.stderr.write(f"CDR write error: {e}\n")
    finally:
        conn.close()


# ── system_log table ──────────────────────────────────────────────────────────

def log_event(
    level: str, event_type: str, message: str,
    call_id: str = None, details: str = None,
) -> None:
    try:
        conn = connect()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO system_log
                    (timestamp, level, component, event_type, message, call_id, details)
                VALUES (NOW(),%s,'agi',%s,%s,%s,%s)
                """,
                (level, event_type, message[:1000], call_id, details),
            )
        conn.commit()
    except Exception as e:
        sys.stderr.write(f"system_log write error: {e}\n")
    finally:
        conn.close()


# ── caller_preferences table ──────────────────────────────────────────────────

def upsert_language_preference(caller_id: str, language: str) -> bool:
    try:
        conn = connect()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO caller_preferences (caller_id, language, updated_at)
                VALUES (%s, %s, NOW())
                ON DUPLICATE KEY UPDATE language = VALUES(language), updated_at = NOW()
                """,
                (caller_id, language),
            )
        conn.commit()
        return True
    except Exception as e:
        sys.stderr.write(f"DB error (language pref upsert): {e}\n")
        return False
    finally:
        conn.close()


def update_call_language(call_id: str, language: str) -> bool:
    try:
        conn = connect()
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE calls SET language = %s WHERE call_id = %s",
                (language, call_id),
            )
        conn.commit()
        return True
    except Exception as e:
        sys.stderr.write(f"DB error (call language update): {e}\n")
        return False
    finally:
        conn.close()

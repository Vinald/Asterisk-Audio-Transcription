#!/usr/bin/env python3
"""
ai_assistant.py — Sunbird/Hashie AI voice assistant for Asterisk IVR.

Called by Asterisk dialplan as:
  AGI(ai_assistant.py,/tmp/input-<CALLID>-<N>.wav,<question_number>,<lang>)

Flow: validate audio → POST /pipeline → download response → play back.
Writes Q1/Q2 data to `calls`, CDR after Q2, errors to `system_log`.
"""

import os
import sys
from datetime import datetime

from agi_lib import agi_io, audio, db, pipeline

SPEAKERS = {
    "lug": 248, "eng": 248, "ach": 241,
    "teo": 242, "nyn": 243, "lgg": 245, "swa": 246,
}

LANGUAGE_NAMES = {
    "eng": "English",
    "lug": "Luganda",
    "ach": "Acholi",
    "teo": "Ateso",
    "nyn": "Runyankore",
    "lgg": "Lugbara",
    "swa": "Swahili",
}


def resolve_language(code: str) -> str:
    return LANGUAGE_NAMES.get(code, code)


def validate_audio(path: str) -> None:
    if not path or not os.path.exists(path):
        raise FileNotFoundError(f"Input audio not found: {path}")
    size = os.path.getsize(path)
    if size < 1000:
        raise ValueError(f"Audio too small ({size} bytes) — was anything recorded?")


def save_q1(call_id, caller_id, extension, language, result) -> None:
    timing = result.get("timing", {})
    db.insert_call_q1(
        call_id=call_id,
        caller_id=caller_id,
        extension=extension,
        language=language,
        speaker_id=result.get("speaker_id"),
        status="in_progress",
        input_text=result.get("input_text", ""),
        output_text=result.get("output_text", ""),
        detected_language=resolve_language(result.get("detected_language", "eng")),
        input_audio=os.path.basename(result["_input_wav"]),
    )
    db.insert_call_metrics(
        call_id=call_id,
        question_number=1,
        audio_url=result.get("output_audio_url", ""),
        stt_duration=timing.get("stt_duration"),
        agent_duration=timing.get("agent_duration"),
        tts_duration=timing.get("tts_duration"),
        total_duration=timing.get("total_duration"),
    )


def save_q2(call_id, result) -> None:
    timing = result.get("timing", {})
    db.update_call_q2(
        call_id=call_id,
        input_text=result.get("input_text", ""),
        output_text=result.get("output_text", ""),
        detected_language=resolve_language(result.get("detected_language", "eng")),
        input_audio=os.path.basename(result["_input_wav"]),
    )
    db.insert_call_metrics(
        call_id=call_id,
        question_number=2,
        audio_url=result.get("output_audio_url", ""),
        stt_duration=timing.get("stt_duration"),
        agent_duration=timing.get("agent_duration"),
        tts_duration=timing.get("tts_duration"),
        total_duration=timing.get("total_duration"),
    )


def prepare_response_audio(audio_url: str, call_id: str, question_number: int) -> str:
    response_wav = f"/tmp/ai_response_{call_id}_{question_number}.wav"
    return audio.download_and_prepare(audio_url, response_wav)


def set_channel_variables(response_wav: str, result: dict) -> None:
    playback_path = response_wav.replace(".wav", "")
    agi_io.set_variable("AI_RESPONSE_FILE", playback_path)
    agi_io.set_variable("USER_INPUT",        result.get("input_text", ""))
    agi_io.set_variable("AI_RESPONSE",       result.get("output_text", ""))
    agi_io.set_variable("DETECTED_LANG",     result.get("detected_language", ""))


def handle_success(call_id, question_number, caller_id, extension, language,
                   input_wav, start_time, result) -> None:
    result["_input_wav"] = input_wav

    audio_url = result.get("output_audio_url", "")
    if not audio_url or audio_url == "null":
        raise RuntimeError("Pipeline did not return an audio URL")

    response_wav = prepare_response_audio(audio_url, call_id, question_number)
    set_channel_variables(response_wav, result)

    if question_number == 1:
        save_q1(call_id, caller_id, extension, language, result)
    else:
        save_q2(call_id, result)
        db.insert_cdr(call_id, caller_id, extension, start_time, datetime.now())

    db.log_event("INFO", "agi_complete",
                 f"Q{question_number} processed successfully", call_id=call_id)
    agi_io.verbose(f"=== AGI COMPLETE Q{question_number} ===")


def handle_error(call_id, question_number, caller_id, extension, input_wav,
                 start_time, err) -> None:
    err_msg = str(err)
    sys.stderr.write(f"AGI error: {err_msg}\n")
    agi_io.verbose(f"ERROR: {err_msg}")
    agi_io.set_variable("AI_RESPONSE_FILE", "")

    db.log_event("ERROR", "agi_error", err_msg[:500],
                 call_id=call_id, details=f"Q{question_number} input={input_wav}")
    db.insert_error_call(call_id, question_number, caller_id, extension)
    db.insert_cdr(call_id, caller_id, extension, start_time, datetime.now(),
                  disposition="ANSWERED")


def main() -> None:
    agi_env = agi_io.read_env()

    input_wav       = sys.argv[1] if len(sys.argv) > 1 else None
    question_number = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    language        = sys.argv[3] if len(sys.argv) > 3 else None

    caller_id  = agi_env.get("agi_callerid", "unknown")
    extension  = agi_env.get("agi_dnid", agi_env.get("agi_extension", "unknown"))
    call_id    = sys.argv[4] if len(sys.argv) > 4 else agi_env.get("agi_uniqueid", "unknown")
    start_time = datetime.now()

    agi_io.verbose(f"=== AGI START Q{question_number} caller={caller_id} call={call_id} ===")

    try:
        validate_audio(input_wav)
        audio.set_world_readable(input_wav)

        result = pipeline.call(input_wav, call_id=call_id)
        agi_io.verbose(f"User said: {result.get('input_text', '')[:80]}")
        agi_io.verbose(f"Language: {result.get('detected_language')}  "
                       f"Response: {result.get('output_text', '')[:80]}")

        handle_success(call_id, question_number, caller_id, extension,
                       language, input_wav, start_time, result)
    except Exception as e:
        handle_error(call_id, question_number, caller_id, extension,
                     input_wav, start_time, e)


if __name__ == "__main__":
    main()

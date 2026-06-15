"""Full audio pipeline orchestration: STT -> agent -> TTS."""

import logging
import time

from sqlalchemy.orm import Session

from app.clients import hashie, sunbird
from app.core.config import settings
from app.services._utils import temp_audio
from app.services.events import log_event

log = logging.getLogger(__name__)


def _run(audio_path: str, language: str | None, speaker_id: int | None, auto_detect: bool) -> dict:
    timing = {}

    log.info("Step 1: Transcribing audio")
    t0 = time.time()
    transcribed_text = sunbird.speech_to_text(audio_path, language)
    timing["stt_duration"] = time.time() - t0
    log.info("  Transcribed: %.80r  (%.2fs)", transcribed_text, timing["stt_duration"])

    if auto_detect and not language:
        log.info("Step 2: Detecting language")
        t0 = time.time()
        detected_language = sunbird.detect_language(transcribed_text)
        timing["language_detection_duration"] = time.time() - t0
        log.info("  Detected: %s  (%.2fs)", detected_language, timing["language_detection_duration"])
    else:
        detected_language = language or "eng"
        timing["language_detection_duration"] = 0
        log.info("Step 2: Using specified language: %s", detected_language)

    log.info("Step 3: Processing with AI agent")
    t0 = time.time()
    agent_response, conversation_id = hashie.chat(transcribed_text, detected_language)
    timing["agent_duration"] = time.time() - t0
    log.info("  Response: %.80r  (%.2fs)", agent_response, timing["agent_duration"])

    log.info("Step 4: Converting response to audio")
    t0 = time.time()
    if speaker_id is None:
        speaker_id = settings.speaker_for(detected_language)
    tts_result = sunbird.text_to_speech(agent_response, speaker_id)
    timing["tts_duration"] = time.time() - t0
    log.info("  Audio URL: %s  (%.2fs)", tts_result["audio_url"], timing["tts_duration"])

    timing["total_duration"] = sum(
        v for k, v in timing.items() if k != "language_detection_duration"
    )
    log.info("PIPELINE COMPLETE — total: %.2fs", timing["total_duration"])
    return {
        "input_text": transcribed_text,
        "output_text": agent_response,
        "detected_language": detected_language,
        "output_audio_url": tts_result["audio_url"],
        "speaker_id": speaker_id,
        "conversation_id": conversation_id,
        "metadata": tts_result,
        "timing": timing,
    }

 
def run_pipeline(
    db: Session,
    audio_bytes: bytes,
    filename: str,
    language: str | None,
    speaker_id: int | None,
    auto_detect: bool,
    call_id: str | None,
) -> dict:
    with temp_audio("pipeline") as path:
        with open(path, "wb") as f:
            f.write(audio_bytes)
        try:
            result = _run(path, language, speaker_id, auto_detect)
        except Exception as e:
            log_event(db, "ERROR", "pipeline", "pipeline_error", str(e)[:500], call_id=call_id)
            raise

    log_event(db, "INFO", "pipeline", "pipeline_complete", f"Pipeline processed {filename}", call_id=call_id)
    return result

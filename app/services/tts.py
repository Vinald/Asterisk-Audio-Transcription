"""Text-to-speech synthesis service."""

from app.core.config import settings
from app.clients.sunbird import text_to_speech

SPEAKERS = settings.speakers  # property — language → default speaker ID


def get_speakers() -> dict:
    """Return the map of language codes to default TTS speaker IDs."""
    return SPEAKERS


def resolve_speaker(language: str, speaker_id: int | None) -> int:
    """Return *speaker_id* if provided, otherwise the default speaker for *language*."""
    return speaker_id if speaker_id is not None else SPEAKERS.get(language, 248)


def synthesize(text: str, language: str, speaker_id: int | None) -> dict:
    """
    Convert *text* to speech and return a dict with the audio URL, resolved
    speaker ID, language, and raw TTS metadata.
    """
    sid = resolve_speaker(language, speaker_id)
    result = text_to_speech(text, speaker_id=sid)
    return {
        "audio_url": result["audio_url"],
        "speaker_id": sid,
        "language": language,
        "metadata": result,
    }

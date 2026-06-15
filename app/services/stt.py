"""Speech-to-text and language detection services."""

from app.clients.sunbird import detect_language, speech_to_text
from app.services._utils import temp_audio


def transcribe(audio_bytes: bytes, language: str | None) -> str:
    """Save *audio_bytes* to a temp file, transcribe it, and return the text."""
    with temp_audio("stt") as path:
        with open(path, "wb") as f:
            f.write(audio_bytes)
        return speech_to_text(path, language=language)


def identify_language(text: str) -> str:
    """Return the BCP-47 language code detected for *text*."""
    return detect_language(text)

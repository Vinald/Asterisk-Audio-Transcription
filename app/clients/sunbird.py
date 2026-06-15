import logging
import os

import requests

from app.clients._retry import retry_request
from app.core.config import settings

log = logging.getLogger(__name__)
_HEADERS = settings.sunbird_headers


def speech_to_text(audio_path: str, language: str | None = None) -> str:
    if not os.path.exists(audio_path):
        raise FileNotFoundError(
            f"Audio file not found: {audio_path}\n"
            f"Current working directory: {os.getcwd()}"
        )

    data = {}
    if language:
        data["language"] = language

    with open(audio_path, "rb") as fh:
        files = {"audio": (os.path.basename(audio_path), fh, "audio/wav")}

        def _req():
            return requests.post(settings.STT_URL, headers=_HEADERS, files=files, data=data, timeout=60)

        try:
            response = retry_request(_req)
            if response.status_code == 401:
                raise Exception("STT auth failed (401). Check AUTH_TOKEN in .env.")
            response.raise_for_status()
        except requests.exceptions.Timeout:
            raise Exception("STT API timeout — check Sunbird API reachability")
        except requests.exceptions.ConnectionError:
            raise Exception("Cannot connect to Sunbird API — check internet connection")
        except requests.exceptions.RequestException as e:
            raise Exception(f"STT API error: {e}")

    return response.json()["audio_transcription"]


def detect_language(text: str) -> str:
    headers = {**_HEADERS, "Content-Type": "application/json"}
    payload = {"text": text.strip().strip("\"'")[:200]}

    def _req():
        return requests.post(settings.LANGUAGE_ID_URL, headers=headers, json=payload, timeout=30)

    try:
        response = retry_request(_req)
        response.raise_for_status()
        result = response.json()
        if isinstance(result, dict):
            return result.get("language") or result.get("detected_language") or "eng"
        return result if isinstance(result, str) else "eng"
    except requests.exceptions.RequestException as e:
        log.warning("Language detection failed (%s), defaulting to 'eng'", e)
        return "eng"


def text_to_speech(text: str, speaker_id: int = 248) -> dict:
    headers = {**_HEADERS, "Content-Type": "application/json"}
    payload = {"response_mode": "url", "speaker_id": speaker_id, "text": text}

    def _req():
        return requests.post(settings.TTS_URL, headers=headers, json=payload, timeout=60)

    try:
        response = retry_request(_req)
        if response.status_code == 401:
            raise Exception("TTS auth failed (401). Check AUTH_TOKEN in .env.")
        response.raise_for_status()
    except requests.exceptions.Timeout:
        raise Exception("TTS API timeout — check Sunbird API reachability")
    except requests.exceptions.ConnectionError:
        raise Exception("Cannot connect to Sunbird API — check internet connection")
    except requests.exceptions.RequestException as e:
        raise Exception(f"TTS API error: {e}")

    return response.json()

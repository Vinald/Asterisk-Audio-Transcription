"""HTTP client for the local pipeline API."""

import os

import requests

from . import agi_io

PIPELINE_URL = "http://localhost:8000/api/v1/pipeline"
_TOKEN = os.environ.get("API_TOKEN", "")


def call(audio_path: str, call_id: str = None) -> dict:
    """POST audio to /pipeline and return the JSON result."""
    agi_io.verbose("Calling local pipeline service...")
    try:
        extra = {"auto_detect": "True"}
        if call_id:
            extra["call_id"] = call_id
        with open(audio_path, "rb") as f:
            response = requests.post(
                PIPELINE_URL,
                files={"audio": (os.path.basename(audio_path), f, "audio/wav")},
                data=extra,
                headers={"Authorization": f"Bearer {_TOKEN}"},
                timeout=270,
            )
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            "Cannot connect to pipeline service at localhost:8000. "
            "Check: sudo systemctl status stt-tts-pipeline"
        )
    except requests.exceptions.Timeout:
        raise RuntimeError("Pipeline service timed out")

    if response.status_code != 200:
        raise RuntimeError(
            f"Pipeline error ({response.status_code}): {response.text[:200]}"
        )

    result = response.json()
    if not result.get("success"):
        raise RuntimeError(
            f"Pipeline returned error: {result.get('error', 'unknown')}"
        )

    return result

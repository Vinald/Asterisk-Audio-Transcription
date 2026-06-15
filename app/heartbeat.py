"""
Heartbeat service — keeps Sunbird AI API endpoints warm.
Runs as a background daemon thread inside the FastAPI process.
"""

import logging
import threading
import time

import requests

from app.core.config import settings

log = logging.getLogger(__name__)

ENDPOINTS = {
    "stt": settings.STT_URL,
    "tts": settings.TTS_URL,
    "language_id": settings.LANGUAGE_ID_URL,
}


def _headers():
    return {"accept": "application/json", "Authorization": f"Bearer {settings.AUTH_TOKEN}"}


def ping_endpoint(name: str, url: str) -> bool:
    try:
        h = {**_headers(), "Content-Type": "application/json"}
        if name in ("stt", "tts"):
            response = requests.post(url, headers=h, json={}, timeout=5)
        elif name == "language_id":
            response = requests.post(url, headers=h, json={"text": "ping"}, timeout=5)
        else:
            response = requests.head(url, headers=_headers(), timeout=5)
        ok = response.ok or response.status_code in (200, 400, 405)
        log.info("heartbeat %s: %s", name, "ok" if ok else f"error {response.status_code}")
        return ok
    except Exception as e:
        log.warning("heartbeat %s: %s", name, e)
        return False


def heartbeat_loop(interval: int = 300):
    log.info("Heartbeat started (interval: %ds)", interval)
    while True:
        try:
            log.debug("Heartbeat tick")
            for name, url in ENDPOINTS.items():
                ping_endpoint(name, url)
        except Exception as e:
            log.error("Heartbeat error: %s", e)
        time.sleep(interval)


def start_heartbeat_daemon(interval: int = 300) -> threading.Thread:
    thread = threading.Thread(target=heartbeat_loop, args=(interval,), daemon=True)
    thread.start()
    log.info("Heartbeat daemon started (interval: %ds)", interval)
    return thread


if __name__ == "__main__":
    try:
        heartbeat_loop(interval=300)
    except KeyboardInterrupt:
        log.info("Heartbeat stopped")

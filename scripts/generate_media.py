#!/usr/bin/env python3
"""
generate_media.py — Generate all HASH IVR prompt audio files using Sunbird TTS.

Reads AUTH_TOKEN from .env, calls Sunbird TTS for each prompt, downloads
the audio, converts to 8 kHz mono 16-bit PCM (Asterisk format) with sox,
and saves to media/ inside the project root.

Usage:
    python scripts/generate_media.py           # generate all missing files
    python scripts/generate_media.py --force   # regenerate even if file exists

Prerequisites:
    - .env with a valid AUTH_TOKEN
    - sox installed  (sudo apt install sox)
    - python -m pip install requests python-dotenv
"""

import argparse
import os
import subprocess
import sys
import time

import requests
from dotenv import load_dotenv

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEDIA_DIR = os.path.join(PROJECT_DIR, "media")
TTS_URL = "https://api.sunbird.ai/tasks/modal/tts"

load_dotenv(os.path.join(PROJECT_DIR, ".env"))
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "")

ENGLISH_SPEAKER = 248   # Sunbird speaker ID for English
LUGANDA_SPEAKER = 248   # Sunbird speaker ID for Luganda (female)

# ── Prompt definitions ────────────────────────────────────────────────────────
# Each entry: (filename_without_ext, text, speaker_id)
PROMPTS = [
    # Pre-language-selection (English — language not yet known)
    (
        "hash-greeting",
        "Hello friend! Welcome to the H-ASH conversational agent",
        ENGLISH_SPEAKER,
    ),
    (
        "hash-language-menu",
        (
            "To interact with the conversational agent in English, press 1. "
            "Mu Luganda, nyiga biri."
        ),
        ENGLISH_SPEAKER,
    ),
    (
        "hash-invalid-lang",
        (
            "That is not a valid selection. "
            "To interact with the conversational agent in English, press 1. "
            "Mu Luganda, nyiga biri."
        ),
        ENGLISH_SPEAKER,
    ),

    # English prompts
    (
        "hash-welcome-english",
        (
            "Hello friend! You have selected English. "
            "Welcome to the H-ASH conversational agent, "
            "a HUB for Artificial Intelligence in Maternal, "
            "Sexual and Reproductive Health!"
        ),
        ENGLISH_SPEAKER,
    ),
    (
        "hash-question-prompt-english",
        (
            "Do you have any health question related to maternal, sexual or reproductive health "
            "that you would like to ask the conversational agent? "
            "You can ask two questions. Press 1 for Yes, press 2 for No."
        ),
        ENGLISH_SPEAKER,
    ),
    (
        "hash-ask-q1-english",
        "After the beep, please proceed to ask the first question.",
        ENGLISH_SPEAKER,
    ),
    (
        "hash-processing-english",
        "The conversational agent is processing your request. Please wait.",
        ENGLISH_SPEAKER,
    ),
    (
        "hash-ask-q2-english",
        "After the beep, please proceed to ask the second question.",
        ENGLISH_SPEAKER,
    ),
    (
        "hash-goodbye-english",
        "Goodbye friend, stay well.",
        ENGLISH_SPEAKER,
    ),
    (
        "hash-invalid-choice-english",
        "That is not a valid selection. Press 1 for Yes, press 2 for No.",
        ENGLISH_SPEAKER,
    ),
    (
        "hash-error-english",
        "An error has occurred. Goodbye friend, stay well.",
        ENGLISH_SPEAKER,
    ),

    # Luganda prompts
    (
        "hash-welcome-luganda",
        (
            "Oli otya mukwano! Olondedde Luganda. "
            "Tukusanyukidde mu H-ASH conversational agent, "
            "HUB ya Artificial Intelligence mu byafaayo by'obulamu bw'omuzadde, "
            "obulamu bwa ngendo n'obulamu bw'okuzaala!"
        ),
        LUGANDA_SPEAKER,
    ),
    (
        "hash-question-prompt-luganda",
        (
            "Olina ekibuuzo ky'obulamu bw'omuzadde, obulamu bwa ngendo "
            "oba obulamu bw'okuzaala ky'oyagala okusaba agent? "
            "Osobola okusaba ebibuuzo bibiri. Nyiga 1 Yee, nyiga 2 Nedda."
        ),
        LUGANDA_SPEAKER,
    ),
    (
        "hash-ask-q1-luganda",
        "Oluvannyuma lw'omubuguma, tusaba okwogera ekibuuzo kyo eky'olubereberye.",
        LUGANDA_SPEAKER,
    ),
    (
        "hash-processing-luganda",
        "Agent ekola ku kibuuzo kyo. Simama nga tusaasira.",
        LUGANDA_SPEAKER,
    ),
    (
        "hash-ask-q2-luganda",
        "Oluvannyuma lw'omubuguma, tusaba okwogera ekibuuzo kyo eky'okubiri.",
        LUGANDA_SPEAKER,
    ),
    (
        "hash-goodbye-luganda",
        "Webale ebibuuzo byo. Wano mukwano, bulamu obeere bulungi.",
        LUGANDA_SPEAKER,
    ),
    (
        "hash-invalid-choice-luganda",
        "Ekyo si kulonza okutuukirivu. Nyiga 1 Yee, nyiga 2 Nedda.",
        LUGANDA_SPEAKER,
    ),
    (
        "hash-error-luganda",
        "Waliwo ensobi. Wano mukwano, bulamu obeere bulungi.",
        LUGANDA_SPEAKER,
    ),
]


def check_prerequisites() -> None:
    if not AUTH_TOKEN or "placeholder" in AUTH_TOKEN.lower() or "your_" in AUTH_TOKEN.lower():
        print("[!] AUTH_TOKEN not configured in .env")
        print("    Copy .env.example to .env and set a valid Sunbird token:")
        print("    cp .env.example .env && nano .env")
        sys.exit(1)

    result = subprocess.run(["which", "sox"], capture_output=True)
    if result.returncode != 0:
        print("[!] sox not found — install it:")
        print("    sudo apt install sox")
        sys.exit(1)


def tts_request(text: str, speaker_id: int) -> str:
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {"response_mode": "url", "speaker_id": speaker_id, "text": text}

    for attempt in range(3):
        try:
            resp = requests.post(TTS_URL, headers=headers, json=payload, timeout=60)
            if resp.status_code == 401:
                print("\n[!] TTS Authentication Failed (401)")
                print("    Your AUTH_TOKEN is invalid or expired.")
                print("    Get a new token at https://api.sunbird.ai and update .env")
                sys.exit(1)
            resp.raise_for_status()
            return resp.json()["audio_url"]
        except requests.exceptions.RequestException as exc:
            if attempt < 2:
                wait = 3 * (2 ** attempt)
                print(f"      retry {attempt + 1}/3 in {wait}s — {exc}")
                time.sleep(wait)
            else:
                raise


def download_audio(url: str, path: str) -> None:
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    with open(path, "wb") as f:
        f.write(resp.content)


def convert_for_asterisk(src: str, dst: str) -> None:
    subprocess.run(
        ["sox", src, "-r", "8000", "-c", "1", "-b", "16", "-e", "signed-integer", dst],
        check=True,
        stderr=subprocess.DEVNULL,
    )


def generate_one(name: str, text: str, speaker_id: int, force: bool) -> str:
    out_path = os.path.join(MEDIA_DIR, f"{name}.wav")
    tmp_path = out_path + ".tmp.wav"

    if os.path.exists(out_path) and not force:
        return "skip"

    try:
        audio_url = tts_request(text, speaker_id)
        download_audio(audio_url, tmp_path)
        convert_for_asterisk(tmp_path, out_path)
        os.remove(tmp_path)
        return "ok"
    except Exception as exc:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise exc
    finally:
        time.sleep(0.4)  # gentle rate-limiting between API calls


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate HASH IVR audio prompts via Sunbird TTS")
    parser.add_argument("--force", action="store_true", help="Regenerate files that already exist")
    args = parser.parse_args()

    check_prerequisites()
    os.makedirs(MEDIA_DIR, exist_ok=True)

    total = len(PROMPTS)
    print(f"HASH IVR audio generator — {total} prompts → {MEDIA_DIR}/")
    print()

    ok = failed = skipped = 0
    for name, text, speaker_id in PROMPTS:
        try:
            status = generate_one(name, text, speaker_id, args.force)
            if status == "skip":
                print(f"  [skip] {name}.wav")
                skipped += 1
            else:
                print(f"  [ok]   {name}.wav")
                ok += 1
        except Exception as exc:
            print(f"  [FAIL] {name}.wav — {exc}")
            failed += 1

    print()
    print(f"Done.  Generated: {ok}  Skipped (already exist): {skipped}  Failed: {failed}")

    if failed:
        print(f"\n[!] {failed} file(s) failed — fix the errors above and re-run.")
        print("    Use --force to regenerate files that already exist.")
        sys.exit(1)

    print()
    print("Next step: copy files to Asterisk and reload dialplan:")
    print("  sudo bash install.sh")


if __name__ == "__main__":
    main()

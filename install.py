#!/usr/bin/env python3
"""
install.py — Asterisk Audio Generator installer.

Sets up the Python virtual environment, installs dependencies,
validates the environment, and prints how to start the app.

Usage:
    python install.py
"""

import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(PROJECT_DIR, ".venv")
MEDIA_DIR = os.path.join(PROJECT_DIR, "media")
MODEL_DIR = os.path.join(PROJECT_DIR, "models")
ENV_FILE = os.path.join(PROJECT_DIR, ".env")
ENV_EXAMPLE = os.path.join(PROJECT_DIR, ".env.example")
REQUIREMENTS = os.path.join(PROJECT_DIR, "requirements.txt")

KOKORO_BASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
KOKORO_FILES = {
    "kokoro-v1.0.int8.onnx": f"{KOKORO_BASE}/kokoro-v1.0.int8.onnx",  # ~88 MB, CPU-optimised
    "voices-v1.0.bin":       f"{KOKORO_BASE}/voices-v1.0.bin",         # ~27 MB
}

GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
RESET = "\033[0m"


def ok(msg):
    print(f"{GREEN}✓ {msg}{RESET}")


def warn(msg):
    print(f"{YELLOW}[!] {msg}{RESET}")


def die(msg):
    print(f"{RED}[!] {msg}{RESET}")
    sys.exit(1)


def step(title):
    print(f"\n=== {title} ===")


# ── 1. Python version ──────────────────────────────────────────────────────────
step("1. Python version")
if sys.version_info < (3, 10):
    die(f"Python 3.10+ required (found {sys.version})")
ok(f"Python {sys.version.split()[0]}")


# ── 2. sox + MP3 support ───────────────────────────────────────────────────────
step("2. System dependencies")
if shutil.which("sox") is None:
    die(
        "sox not found.\n"
        "  Linux:  sudo apt install sox libsox-fmt-mp3\n"
        "  Mac:    brew install sox"
    )
ok("sox found")

# Verify sox can actually encode MP3 (requires libsox-fmt-mp3 on Linux)
print("[*] Checking sox MP3 encoding support...")
_fd_wav, _tmp_wav = tempfile.mkstemp(suffix=".wav")
os.close(_fd_wav)
_fd_mp3, _tmp_mp3 = tempfile.mkstemp(suffix=".mp3")
os.close(_fd_mp3)
try:
    subprocess.run(
        ["sox", "-n", "-r", "8000", "-c", "1", "-b", "16", _tmp_wav, "trim", "0", "0.05"],
        check=True, capture_output=True,
    )
    _res = subprocess.run(
        ["sox", _tmp_wav, "-r", "8000", "-c", "1", _tmp_mp3],
        capture_output=True,
    )
    if _res.returncode != 0 or not os.path.exists(_tmp_mp3) or os.path.getsize(_tmp_mp3) == 0:
        die(
            "sox cannot encode MP3. Install MP3 support:\n"
            "  Linux:  sudo apt install libsox-fmt-mp3\n"
            "  Mac:    brew install sox  (includes MP3 via lame)"
        )
    ok("sox MP3 encoding verified")
finally:
    for _p in [_tmp_wav, _tmp_mp3]:
        if os.path.exists(_p):
            os.unlink(_p)


# ── 3. Virtual environment ─────────────────────────────────────────────────────
step("3. Virtual environment")
if not os.path.isdir(VENV_DIR):
    print("[*] Creating .venv ...")
    subprocess.run([sys.executable, "-m", "venv", VENV_DIR], check=True)
    ok(".venv created")
else:
    ok(".venv already exists")

python = os.path.join(VENV_DIR, "bin", "python") if os.name != "nt" else os.path.join(VENV_DIR, "Scripts", "python.exe")
pip = os.path.join(VENV_DIR, "bin", "pip") if os.name != "nt" else os.path.join(VENV_DIR, "Scripts", "pip.exe")


# ── 4. Dependencies ────────────────────────────────────────────────────────────
step("4. Python dependencies")
print("[*] Installing packages (this may take a moment) ...")
subprocess.run([pip, "install", "--upgrade", "pip", "-q"], check=True)
subprocess.run([pip, "install", "-r", REQUIREMENTS, "-q"], check=True)
ok("All packages installed")

# Verify edge-tts can reach Microsoft's neural TTS service
print("[*] Checking edge-tts connectivity...")
_edge_tts = os.path.join(VENV_DIR, "bin", "edge-tts") if os.name != "nt" else os.path.join(VENV_DIR, "Scripts", "edge-tts.exe")
_voice_check = subprocess.run([_edge_tts, "--list-voices"], capture_output=True, text=True)
if _voice_check.returncode != 0:
    warn("edge-tts --list-voices failed — English/Swahili TTS may not work (check network)")
else:
    ok("edge-tts reachable — English and Swahili voices available")

# Check AUTH_TOKEN for Luganda (Sunbird AI) — optional but required for Luganda
print("[*] Checking AUTH_TOKEN for Luganda (Sunbird AI)...")
_auth = ""
if os.path.exists(ENV_FILE):
    with open(ENV_FILE) as _f:
        for _line in _f:
            if _line.startswith("AUTH_TOKEN="):
                _auth = _line.split("=", 1)[1].strip()
                break
if not _auth or "your_" in _auth.lower():
    warn("AUTH_TOKEN not set — Luganda voices will return an error. English and Swahili work fine without it.")
    warn("To enable Luganda: add AUTH_TOKEN=<your_sunbird_token> to .env and restart.")
else:
    ok("AUTH_TOKEN found — Luganda (Sunbird AI) enabled")


# ── 5. Kokoro TTS model files ─────────────────────────────────────────────────
step("5. Kokoro TTS models (English)")
os.makedirs(MODEL_DIR, exist_ok=True)

def _download(filename, url):
    dest = os.path.join(MODEL_DIR, filename)
    if os.path.exists(dest) and os.path.getsize(dest) > 1024 * 1024:
        ok(f"{filename} already present")
        return
    print(f"[*] Downloading {filename} ...")
    def _progress(count, block, total):
        if total > 0:
            pct = min(100, count * block * 100 // total)
            print(f"\r    {pct:3d}%", end="", flush=True)
    try:
        urllib.request.urlretrieve(url, dest, reporthook=_progress)
        print()
        size_mb = os.path.getsize(dest) // (1024 * 1024)
        ok(f"{filename} downloaded ({size_mb} MB)")
    except Exception as exc:
        print()
        if os.path.exists(dest):
            os.unlink(dest)
        die(f"Failed to download {filename}: {exc}\nURL: {url}")

for _fname, _url in KOKORO_FILES.items():
    _download(_fname, _url)


# ── 6. media/ directory ────────────────────────────────────────────────────────
step("6. Media directory")
os.makedirs(MEDIA_DIR, exist_ok=True)
ok(f"media/ ready at {MEDIA_DIR}")


# ── Done ───────────────────────────────────────────────────────────────────────
print(f"""
{'=' * 48}
{GREEN}✓ Installation complete!{RESET}
{'=' * 48}

Start the app:
  source .venv/bin/activate
  python app.py

Or with uvicorn directly:
  .venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000 --reload

Or with Docker:
  docker compose up -d

Then open: http://localhost:8000
""")

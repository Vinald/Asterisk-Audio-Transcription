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

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(PROJECT_DIR, ".venv")
MEDIA_DIR = os.path.join(PROJECT_DIR, "media")
ENV_FILE = os.path.join(PROJECT_DIR, ".env")
ENV_EXAMPLE = os.path.join(PROJECT_DIR, ".env.example")
REQUIREMENTS = os.path.join(PROJECT_DIR, "requirements.txt")

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


# ── 2. sox ─────────────────────────────────────────────────────────────────────
step("2. System dependencies")
if shutil.which("sox") is None:
    die(
        "sox not found.\n"
        "  Linux:  sudo apt install sox\n"
        "  Mac:    brew install sox"
    )
ok("sox found")


# ── 3. .env ────────────────────────────────────────────────────────────────────
step("3. Environment file")
if not os.path.exists(ENV_FILE):
    if os.path.exists(ENV_EXAMPLE):
        shutil.copy(ENV_EXAMPLE, ENV_FILE)
        warn(f".env created from .env.example — open {ENV_FILE} and set AUTH_TOKEN, then re-run.")
        sys.exit(1)
    else:
        die(".env not found. Create it with:\n  echo 'AUTH_TOKEN=your_token_here' > .env")

# Validate AUTH_TOKEN
auth_token = ""
with open(ENV_FILE) as f:
    for line in f:
        if line.startswith("AUTH_TOKEN="):
            auth_token = line.split("=", 1)[1].strip()
            break

if not auth_token or "your_" in auth_token.lower() or "placeholder" in auth_token.lower():
    die("AUTH_TOKEN in .env looks like a placeholder.\nSet a real Sunbird AI token and re-run.")

ok(".env found and AUTH_TOKEN is set")


# ── 4. Virtual environment ─────────────────────────────────────────────────────
step("4. Virtual environment")
if not os.path.isdir(VENV_DIR):
    print("[*] Creating .venv ...")
    subprocess.run([sys.executable, "-m", "venv", VENV_DIR], check=True)
    ok(".venv created")
else:
    ok(".venv already exists")

python = os.path.join(VENV_DIR, "bin", "python") if os.name != "nt" else os.path.join(VENV_DIR, "Scripts", "python.exe")
pip = os.path.join(VENV_DIR, "bin", "pip") if os.name != "nt" else os.path.join(VENV_DIR, "Scripts", "pip.exe")


# ── 5. Dependencies ────────────────────────────────────────────────────────────
step("5. Python dependencies")
print("[*] Installing packages (this may take a moment) ...")
subprocess.run([pip, "install", "--upgrade", "pip", "-q"], check=True)
subprocess.run([pip, "install", "-r", REQUIREMENTS, "-q"], check=True)
ok("All packages installed")


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

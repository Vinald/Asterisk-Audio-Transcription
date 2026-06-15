"""Load project .env and expose DATABASE_URL + parsed DB_CONFIG."""

import os
import re

from dotenv import load_dotenv

_project_dir = os.getenv("STT_TTS_PROJECT_DIR", "")
load_dotenv(os.path.join(_project_dir, ".env"))

DATABASE_URL: str = os.getenv("DATABASE_URL", "")


def _parse_db_url(url: str) -> dict:
    if not url:
        raise RuntimeError(
            "DATABASE_URL is empty. STT_TTS_PROJECT_DIR may not be set in the "
            "Asterisk systemd environment. Re-run install.sh to fix this."
        )
    m = re.match(
        r"mysql(?:\+pymysql)?://([^:]+):([^@]+)@([^:/]+)(?::(\d+))?/(.+)", url
    )
    if not m:
        raise ValueError(f"Cannot parse DATABASE_URL: {url}")
    return {
        "user": m.group(1),
        "password": m.group(2),
        "host": m.group(3),
        "port": int(m.group(4) or 3306),
        "database": m.group(5),
    }


try:
    DB_CONFIG: dict = _parse_db_url(DATABASE_URL)
except (ValueError, RuntimeError):
    DB_CONFIG: dict = {}

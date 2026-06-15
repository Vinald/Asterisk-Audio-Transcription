import asyncio
import logging
import os
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

load_dotenv()

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(name)s — %(message)s")

AUTH_TOKEN = os.getenv("AUTH_TOKEN", "")
TTS_URL = "https://api.sunbird.ai/tasks/modal/tts"
SPEAKERS_URL = "https://api.sunbird.ai/tasks/voice/speakers"
MEDIA_DIR = os.path.join(os.path.dirname(__file__), "media")
FILENAME_MAX_LEN = 100

LANG_NAMES = {
    "eng": "English",
    "lug": "Luganda",
    "ach": "Acholi",
    "teo": "Ateso",
    "nyn": "Runyankore",
    "lgg": "Lugbara",
    "swa": "Swahili",
}

FALLBACK_SPEAKERS = {
    "English":    [{"id": 248, "name": "248 — English (female)"}],
    "Luganda":    [{"id": 248, "name": "248 — Luganda (female)"}],
    "Acholi":     [{"id": 241, "name": "241 — Acholi (female)"}],
    "Ateso":      [{"id": 242, "name": "242 — Ateso (female)"}],
    "Runyankore": [{"id": 243, "name": "243 — Runyankore (female)"}],
    "Lugbara":    [{"id": 245, "name": "245 — Lugbara (female)"}],
    "Swahili":    [{"id": 246, "name": "246 — Swahili (male)"}],
}

# Content-Type → sox format name
_CT_TO_SOX = {
    "audio/mpeg": "mp3", "audio/mp3": "mp3", "audio/x-mpeg": "mp3",
    "audio/ogg": "ogg", "application/ogg": "ogg",
    "audio/flac": "flac",
}

_speakers_cache: dict = {}


def _sox_format(content_type: str) -> tuple[str, str]:
    """Return (sox -t flag, temp file suffix) from a Content-Type header value."""
    ct = content_type.lower().split(";")[0].strip()
    fmt = _CT_TO_SOX.get(ct, "wav")
    return fmt, f".{fmt}"


async def fetch_speakers(client: httpx.AsyncClient) -> dict:
    try:
        resp = await client.get(
            SPEAKERS_URL,
            headers={"Authorization": f"Bearer {AUTH_TOKEN}", "accept": "application/json"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        speaker_list = data if isinstance(data, list) else data.get("speakers", data.get("data", []))

        grouped: dict = {}
        for s in speaker_list:
            raw_lang = (s.get("language") or s.get("lang") or "unknown").strip().lower()
            lang = LANG_NAMES.get(raw_lang, raw_lang.title())
            sid = s.get("id") if s.get("id") is not None else s.get("speaker_id")
            display = s.get("display_name") or s.get("name") or str(sid)
            gender = (s.get("gender") or "").strip()
            label = f"{sid} — {display}" + (f" ({gender})" if gender else "")
            grouped.setdefault(lang, []).append({"id": sid, "name": label})

        if grouped:
            return grouped
        log.warning("fetch_speakers: Sunbird returned an empty speaker list — using fallback")
        return FALLBACK_SPEAKERS
    except Exception as exc:
        log.warning("fetch_speakers failed (%s: %s) — using fallback", type(exc).__name__, exc)
        return FALLBACK_SPEAKERS


os.makedirs(MEDIA_DIR, exist_ok=True)


@asynccontextmanager
async def lifespan(app):
    global _speakers_cache
    if not AUTH_TOKEN:
        log.warning("AUTH_TOKEN is not set — TTS calls will fail. Set it in .env and restart.")

    # Single shared client for the lifetime of the process (fix #7: avoids per-request TLS churn)
    async with httpx.AsyncClient(http2=False) as client:
        app.state.http = client
        _speakers_cache = await fetch_speakers(client)
        log.info("Speakers loaded: %s", list(_speakers_cache.keys()))
        yield


app = FastAPI(title="Asterisk Audio Generator", docs_url=None, redoc_url=None, lifespan=lifespan)
app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))


@app.get("/health")
async def health():
    return {"ok": True}


@app.get("/speakers")
async def speakers():
    return JSONResponse(_speakers_cache)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    # fix #8: offload blocking listdir to thread pool
    all_files = await asyncio.to_thread(os.listdir, MEDIA_DIR)
    files = sorted(f for f in all_files if f.endswith(".mp3"))
    return templates.TemplateResponse("index.html", {"request": request, "files": files})


@app.post("/generate")
async def generate(
    request: Request,
    text: str = Form(...),
    filename: str = Form(...),
    language: str = Form(...),
    speaker_id: int = Form(...),
):
    if not AUTH_TOKEN:
        raise HTTPException(status_code=500, detail="AUTH_TOKEN not set in .env")

    if language not in _speakers_cache:
        raise HTTPException(status_code=400, detail=f"Unknown language: {language}")

    if speaker_id < 1:
        raise HTTPException(status_code=400, detail="Speaker ID must be a positive number")

    # Sanitise filename: strip .mp3 if already present, clean chars, cap, re-add .mp3
    # (fix #12: truncation happens before suffix is added so the cap is exact)
    safe_name = filename.strip().replace(" ", "-")
    safe_name = "".join(c for c in safe_name if c.isalnum() or c in "-_")
    if safe_name.endswith("mp3"):
        safe_name = safe_name[:-3].rstrip(".")
    safe_name = safe_name[:FILENAME_MAX_LEN]
    if not safe_name:
        raise HTTPException(status_code=400, detail="Invalid filename")
    safe_name += ".mp3"

    out_path = os.path.join(MEDIA_DIR, safe_name)
    client: httpx.AsyncClient = request.app.state.http

    # Call Sunbird TTS
    try:
        resp = await client.post(
            TTS_URL,
            headers={
                "accept": "application/json",
                "Authorization": f"Bearer {AUTH_TOKEN}",
                "Content-Type": "application/json",
            },
            json={"response_mode": "url", "speaker_id": speaker_id, "text": text},
            timeout=60,
        )
        if resp.status_code == 401:
            raise HTTPException(status_code=502, detail="Sunbird AUTH_TOKEN rejected (401)")
        resp.raise_for_status()

        # fix #4: explicit missing-key check instead of KeyError → opaque 502
        payload = resp.json()
        audio_url = payload.get("audio_url")
        if not audio_url:
            raise HTTPException(
                status_code=502,
                detail=f"Sunbird response missing audio_url (keys: {list(payload.keys())})",
            )

        dl = await client.get(audio_url, timeout=30)
        dl.raise_for_status()
        audio_bytes = dl.content
        # fix #5: detect actual audio format so sox doesn't misparse the bytes
        sox_fmt, tmp_suffix = _sox_format(dl.headers.get("content-type", ""))

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"TTS request failed: {exc}")

    # Convert to 8 kHz mono MP3 via sox
    tmp_path = None
    try:
        # fix #9 (in app.py context): mkstemp atomically creates the file, no TOCTOU race
        fd, tmp_path = tempfile.mkstemp(suffix=tmp_suffix)
        os.close(fd)
        with open(tmp_path, "wb") as f:
            f.write(audio_bytes)

        # fix #2: asyncio subprocess — does not block the event loop
        proc = await asyncio.create_subprocess_exec(
            "sox", "-t", sox_fmt, tmp_path, "-r", "8000", "-c", "1", out_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise HTTPException(status_code=500, detail=f"sox conversion failed: {stderr.decode()}")

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    return JSONResponse({"filename": safe_name, "url": f"/media/{safe_name}"})


@app.get("/files")
async def list_files():
    all_files = await asyncio.to_thread(os.listdir, MEDIA_DIR)
    files = sorted(f for f in all_files if f.endswith(".mp3"))
    return {"files": files}


@app.delete("/files/{filename}")
async def delete_file(filename: str):
    # fix #3: resolve the full path and assert it stays inside MEDIA_DIR
    media_root = Path(MEDIA_DIR).resolve()
    target = (media_root / filename).resolve()
    if not target.is_relative_to(media_root):
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found")
    target.unlink()
    return {"deleted": filename}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)

import asyncio
import csv
import io
import json
import logging
import os
import tempfile
import wave
from contextlib import asynccontextmanager
from pathlib import Path

import edge_tts
import httpx
import numpy as np
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from kokoro_onnx import Kokoro

load_dotenv()

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(name)s — %(message)s")

AUTH_TOKEN = os.getenv("AUTH_TOKEN", "")   # required for any Sunbird voice (English or Luganda)
SUNBIRD_TTS_URL = "https://api.sunbird.ai/tasks/modal/tts"
MEDIA_DIR = os.path.join(os.path.dirname(__file__), "media")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
KOKORO_MODEL_PATH = os.path.join(MODEL_DIR, "kokoro-v1.0.int8.onnx")
KOKORO_VOICES_PATH = os.path.join(MODEL_DIR, "voices-v1.0.bin")
FILENAME_MAX_LEN = 100
TEXT_MAX_LEN = 5000       # chars; protects all TTS backends from runaway requests
BATCH_MAX_ROWS = 500      # rows; prevents DoS via oversized CSVs
UPLOAD_MAX_BYTES = 2 * 1024 * 1024  # 2 MB CSV limit

# Voice roster — voice ID prefix determines TTS backend:
#   af_/am_/bf_/bm_ → Kokoro TTS (English, local model)
#   sw-*            → edge-tts (Swahili, Microsoft neural)
#   sunbird:*       → Sunbird AI (needs AUTH_TOKEN)
VOICES = {
    "English": [
        # ── Kokoro TTS (local model, highest quality) ──
        {"id": "af_heart",    "name": "Heart — US female (Kokoro)"},
        {"id": "af_bella",    "name": "Bella — US female (Kokoro)"},
        {"id": "af_sarah",    "name": "Sarah — US female (Kokoro)"},
        {"id": "af_nicole",   "name": "Nicole — US female (Kokoro)"},
        {"id": "af_jessica",  "name": "Jessica — US female (Kokoro)"},
        {"id": "am_adam",     "name": "Adam — US male (Kokoro)"},
        {"id": "am_michael",  "name": "Michael — US male (Kokoro)"},
        {"id": "am_liam",     "name": "Liam — US male (Kokoro)"},
        {"id": "bf_emma",     "name": "Emma — GB female (Kokoro)"},
        {"id": "bf_isabella", "name": "Isabella — GB female (Kokoro)"},
        {"id": "bm_george",   "name": "George — GB male (Kokoro)"},
        {"id": "bm_lewis",    "name": "Lewis — GB male (Kokoro)"},
        # ── Sunbird AI (cloud) ──
        {"id": "sunbird:248", "name": "Sunbird 248 — English female (Sunbird)"},
    ],
    "Luganda": [
        {"id": "sunbird:248", "name": "Sunbird — Luganda (female)"},
    ],
    "Swahili": [
        {"id": "sw-KE-ZuriNeural",   "name": "Zuri — Swahili KE (female)"},
        {"id": "sw-KE-RafikiNeural", "name": "Rafiki — Swahili KE (male)"},
        {"id": "sw-TZ-RehemaNeural", "name": "Rehema — Swahili TZ (female)"},
        {"id": "sw-TZ-DaudiNeural",  "name": "Daudi — Swahili TZ (male)"},
    ],
}

_KOKORO_VOICES = {v["id"] for v in VOICES["English"] if not v["id"].startswith("sunbird:")}
_VALID_VOICES = {v["id"] for voices in VOICES.values() for v in voices}

os.makedirs(MEDIA_DIR, exist_ok=True)


@asynccontextmanager
async def lifespan(app):
    if not os.path.exists(KOKORO_MODEL_PATH) or not os.path.exists(KOKORO_VOICES_PATH):
        log.error("Kokoro model files missing in models/ — English (Kokoro) TTS will not work")
        log.error("Run: python install.py  (step 5 downloads the models)")
        app.state.kokoro = None
    else:
        log.info("Loading Kokoro TTS model (int8, CPU)...")
        kokoro = await asyncio.to_thread(Kokoro, KOKORO_MODEL_PATH, KOKORO_VOICES_PATH)
        app.state.kokoro = kokoro
        log.info("Kokoro ready")

    if not AUTH_TOKEN:
        log.warning("AUTH_TOKEN not set — Sunbird voices (English/Luganda) will fail. Kokoro English and Swahili work without it.")

    log.info(
        "Asterisk Audio Generator starting — %d voices across %d languages",
        sum(len(v) for v in VOICES.values()),
        len(VOICES),
    )
    async with httpx.AsyncClient(http2=False) as client:
        app.state.http = client
        yield


app = FastAPI(title="Asterisk Audio Generator", docs_url=None, redoc_url=None, lifespan=lifespan)
app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))


@app.get("/health")
async def health():
    return {"ok": True}


@app.get("/speakers")
async def speakers():
    return JSONResponse(VOICES)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    all_files = await asyncio.to_thread(os.listdir, MEDIA_DIR)
    files = sorted(f for f in all_files if f.endswith(".mp3"))
    return templates.TemplateResponse("index.html", {"request": request, "files": files})


async def _do_generate(request: Request, text: str, filename_raw: str, language: str, voice: str, speed: float = 1.0) -> dict:
    """Synthesise text → 8 kHz mono MP3. Returns {filename, url}."""
    if len(text) > TEXT_MAX_LEN:
        raise HTTPException(status_code=400, detail=f"Text too long ({len(text)} chars; limit {TEXT_MAX_LEN})")
    safe_name = filename_raw.strip().replace(" ", "-")
    safe_name = "".join(c for c in safe_name if c.isalnum() or c in "-_")
    if safe_name.endswith(".mp3"):
        safe_name = safe_name[:-4]
    elif safe_name.endswith("mp3"):
        safe_name = safe_name[:-3].rstrip(".")
    safe_name = safe_name[:FILENAME_MAX_LEN]
    if not safe_name:
        raise HTTPException(status_code=400, detail="Invalid filename")
    safe_name += ".mp3"

    out_path = os.path.join(MEDIA_DIR, safe_name)
    tmp_path = None
    sox_fmt = "mp3"

    try:
        if voice in _KOKORO_VOICES:
            # ── Kokoro TTS (English, local) ──────────────────────────────────
            kokoro: Kokoro | None = getattr(request.app.state, "kokoro", None)
            if kokoro is None:
                raise HTTPException(status_code=503, detail="Kokoro model not loaded — see server logs")
            fd, tmp_path = tempfile.mkstemp(suffix=".wav")
            os.close(fd)
            samples, sample_rate = await asyncio.to_thread(
                kokoro.create, text, voice=voice, speed=speed, lang="en-us"
            )
            with wave.open(tmp_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes((samples * 32767).astype(np.int16).tobytes())
            sox_fmt = "wav"

        elif voice.startswith("sunbird:"):
            # ── Sunbird AI (English / Luganda) ───────────────────────────────
            if not AUTH_TOKEN:
                raise HTTPException(status_code=503, detail="Sunbird voices require AUTH_TOKEN in .env")
            speaker_id = int(voice.split(":")[1])
            client: httpx.AsyncClient = request.app.state.http
            resp = await client.post(
                SUNBIRD_TTS_URL,
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
            payload = resp.json()
            audio_url = payload.get("audio_url")
            if not audio_url:
                raise HTTPException(status_code=502, detail=f"Sunbird missing audio_url (keys: {list(payload.keys())})")
            dl = await client.get(audio_url, timeout=30)
            dl.raise_for_status()
            ct = dl.headers.get("content-type", "")
            if "wav" in ct or audio_url.split("?")[0].lower().endswith(".wav"):
                sox_fmt = "wav"
                fd, tmp_path = tempfile.mkstemp(suffix=".wav")
            else:
                sox_fmt = "mp3"
                fd, tmp_path = tempfile.mkstemp(suffix=".mp3")
            os.close(fd)
            with open(tmp_path, "wb") as f:
                f.write(dl.content)

        else:
            # ── edge-tts (Swahili) ────────────────────────────────────────────
            fd, tmp_path = tempfile.mkstemp(suffix=".mp3")
            os.close(fd)
            # Convert speed multiplier to edge-tts rate string: 0.75 → "-25%", 1.25 → "+25%"
            rate = f"{round((speed - 1.0) * 100):+d}%"
            communicate = edge_tts.Communicate(text, voice, rate=rate)
            await communicate.save(tmp_path)

        proc = await asyncio.create_subprocess_exec(
            "sox", "-t", sox_fmt, tmp_path, "-r", "48000", "-c", "1", out_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            # Truncate stderr to avoid leaking full temp paths / system details
            err_snippet = stderr.decode(errors="replace")[:200]
            raise HTTPException(status_code=500, detail=f"Audio conversion failed: {err_snippet}")

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"TTS request failed: {exc}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    return {"filename": safe_name, "url": f"/media/{safe_name}"}


@app.post("/generate")
async def generate(
    request: Request,
    text: str = Form(...),
    filename: str = Form(...),
    language: str = Form(...),
    voice: str = Form(...),
    speed: float = Form(1.0),
):
    if language not in VOICES:
        raise HTTPException(status_code=400, detail=f"Unknown language: {language}")
    valid_for_lang = {v["id"] for v in VOICES[language]}
    if voice not in valid_for_lang:
        raise HTTPException(status_code=400, detail=f"Voice {voice!r} is not available for {language}")
    speed = max(0.5, min(2.0, speed))
    return JSONResponse(await _do_generate(request, text, filename, language, voice, speed))


@app.post("/batch")
async def batch_generate(
    request: Request,
    file: UploadFile = File(...),
    language: str = Form(...),
    voice: str = Form(...),
    speed: float = Form(1.0),
):
    if language not in VOICES:
        raise HTTPException(status_code=400, detail=f"Unknown language: {language}")
    valid_for_lang = {v["id"] for v in VOICES[language]}
    if voice not in valid_for_lang:
        raise HTTPException(status_code=400, detail=f"Voice {voice!r} is not available for {language}")
    speed = max(0.5, min(2.0, speed))

    if file.size is not None and file.size > UPLOAD_MAX_BYTES:
        raise HTTPException(status_code=413, detail=f"CSV too large (limit {UPLOAD_MAX_BYTES // 1024} KB)")
    content = await file.read()
    if len(content) > UPLOAD_MAX_BYTES:
        raise HTTPException(status_code=413, detail=f"CSV too large (limit {UPLOAD_MAX_BYTES // 1024} KB)")
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text_content = content.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise HTTPException(status_code=400, detail="Could not decode CSV — save the file as UTF-8 and try again")

    rows: list[tuple[str, str]] = []
    reader = csv.reader(io.StringIO(text_content))
    for i, row in enumerate(reader):
        if not row or all(not cell.strip() for cell in row):
            continue
        if len(row) < 2:
            continue
        text_val = row[0].strip()
        filename_val = row[1].strip()
        # Skip header row if present
        if i == 0 and text_val.lower() in ("text", "script") and filename_val.lower() in ("filename", "file", "name"):
            continue
        if text_val and filename_val:
            rows.append((text_val, filename_val))

    if not rows:
        raise HTTPException(
            status_code=400,
            detail="CSV has no valid rows. Expected two columns: text, filename (header row optional)",
        )
    if len(rows) > BATCH_MAX_ROWS:
        raise HTTPException(status_code=400, detail=f"CSV has {len(rows)} rows; limit is {BATCH_MAX_ROWS}")

    async def stream():
        yield f"data: {json.dumps({'type': 'total', 'total': len(rows)})}\n\n"
        for i, (txt, fname) in enumerate(rows):
            if await request.is_disconnected():
                break
            yield f"data: {json.dumps({'type': 'start', 'index': i, 'filename': fname})}\n\n"
            try:
                result = await _do_generate(request, txt, fname, language, voice, speed)
                yield f"data: {json.dumps({'type': 'done', 'index': i, 'filename': result['filename'], 'url': result['url']})}\n\n"
            except HTTPException as exc:
                yield f"data: {json.dumps({'type': 'error', 'index': i, 'filename': fname, 'detail': exc.detail})}\n\n"
            except Exception as exc:
                yield f"data: {json.dumps({'type': 'error', 'index': i, 'filename': fname, 'detail': str(exc)})}\n\n"
        yield f"data: {json.dumps({'type': 'complete'})}\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/files")
async def list_files():
    all_files = await asyncio.to_thread(os.listdir, MEDIA_DIR)
    files = sorted(f for f in all_files if f.endswith(".mp3"))
    return {"files": files}


@app.delete("/files/{filename}")
async def delete_file(filename: str):
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

import os
import subprocess
import tempfile

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

load_dotenv()

AUTH_TOKEN = os.getenv("AUTH_TOKEN", "")
TTS_URL = "https://api.sunbird.ai/tasks/modal/tts"
MEDIA_DIR = os.path.join(os.path.dirname(__file__), "media")

SPEAKERS = {
    "English": 248,
    "Luganda": 248,
    "Acholi": 241,
    "Ateso": 242,
    "Runyankore": 243,
    "Lugbara": 245,
    "Swahili": 246,
}

os.makedirs(MEDIA_DIR, exist_ok=True)

app = FastAPI(title="Asterisk Audio Generator", docs_url=None, redoc_url=None)
app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    files = sorted(f for f in os.listdir(MEDIA_DIR) if f.endswith(".wav"))
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "languages": list(SPEAKERS.keys()), "files": files},
    )


@app.post("/generate")
async def generate(
    text: str = Form(...),
    filename: str = Form(...),
    language: str = Form(...),
):
    if not AUTH_TOKEN:
        raise HTTPException(status_code=500, detail="AUTH_TOKEN not set in .env")

    if language not in SPEAKERS:
        raise HTTPException(status_code=400, detail=f"Unknown language: {language}")

    speaker_id = SPEAKERS[language]

    # Sanitise filename
    safe_name = filename.strip().replace(" ", "-")
    safe_name = "".join(c for c in safe_name if c.isalnum() or c in "-_")
    if not safe_name:
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not safe_name.endswith(".wav"):
        safe_name += ".wav"

    out_path = os.path.join(MEDIA_DIR, safe_name)

    # Call Sunbird TTS
    try:
        resp = requests.post(
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
        audio_url = resp.json()["audio_url"]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"TTS request failed: {exc}")

    # Download raw audio to a temp file
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

        dl = requests.get(audio_url, timeout=30)
        dl.raise_for_status()
        with open(tmp_path, "wb") as f:
            f.write(dl.content)

        # Convert to Asterisk format: 8 kHz, mono, 16-bit signed PCM
        result = subprocess.run(
            ["sox", tmp_path, "-r", "8000", "-c", "1", "-b", "16", "-e", "signed-integer", out_path],
            capture_output=True,
        )
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"sox conversion failed: {result.stderr.decode()}")

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
    files = sorted(f for f in os.listdir(MEDIA_DIR) if f.endswith(".wav"))
    return {"files": files}


@app.delete("/files/{filename}")
async def delete_file(filename: str):
    # Prevent path traversal
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    path = os.path.join(MEDIA_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    os.remove(path)
    return {"deleted": filename}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)

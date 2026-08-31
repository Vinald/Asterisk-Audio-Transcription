# Asterisk Audio & Transcription

A web tool for **text-to-speech** (producing Asterisk-compatible mono MP3 audio from
text) and **speech-to-text** (transcribing audio files). Every backend is selectable
per request.

### Text-to-speech

| Language | Provider | Notes |
|---|---|---|
| English (12 voices) | **Kokoro TTS** | Local model — no internet, no API key |
| English (1 voice) | **Sunbird AI** | Cloud — requires `AUTH_TOKEN` |
| Luganda | **Sunbird AI** | Cloud — requires `AUTH_TOKEN` |
| Swahili (4 voices) | **edge-tts** | Microsoft neural cloud — no API key |

### Speech-to-text

| Backend | Coverage | Notes |
|---|---|---|
| **Sunbird AI** | 51 African languages (Luganda, Swahili, Acholi, Ateso, Runyankole, …) | Cloud — reuses `AUTH_TOKEN` |
| **faster-whisper** | ~90 languages, auto-detect | Local model — no API key; downloads on first use |
| **OpenAI Whisper API** | ~90 languages, auto-detect | Cloud — requires `OPENAI_API_KEY` |

---

## Requirements

| Dependency | Install |
|---|---|
| Python 3.10+ | `python3 --version` |
| sox + MP3 encoding | `sudo apt install sox libsox-fmt-mp3` (Linux) or `brew install sox` (Mac) |

---

## Installation

Run the installer once. It checks all dependencies, creates the virtual environment,
downloads the Kokoro model files (~115 MB), and validates connectivity.

```bash
python install.py
```

Steps the installer performs:

1. Python 3.10+ check
2. sox + MP3 encoding verification
3. Create `.venv/`
4. `pip install -r requirements.txt`
5. edge-tts connectivity check
6. Kokoro model download (`models/kokoro-v1.0.int8.onnx` + `voices-v1.0.bin`)
7. `media/` directory creation

The faster-whisper model is **not** downloaded by the installer — it is fetched
automatically (and cached under `~/.cache/huggingface`) the first time you use the
local transcription backend.

### API tokens

| Token | Enables | Where |
|---|---|---|
| `AUTH_TOKEN` | Sunbird TTS voices (Luganda, "Sunbird 248") **and** Sunbird STT | free account at [api.sunbird.ai](https://api.sunbird.ai) |
| `OPENAI_API_KEY` | OpenAI Whisper STT backend (optional) | [platform.openai.com](https://platform.openai.com) |

```bash
cp .env.example .env
# edit .env and set:  AUTH_TOKEN=<your_sunbird_token>
```

English (Kokoro) and Swahili (edge-tts) voices, and the local faster-whisper
transcription backend, all work without any token.

---

## Running

```bash
source .venv/bin/activate
python app.py
```

Then open **http://localhost:8000** in your browser.

Or with uvicorn directly:

```bash
.venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

Or with Docker:

```bash
docker compose up -d
```

---

## Using the UI

### Single file (text-to-speech)

1. Select **Language** and **Voice** from the dropdowns.
2. Type the text to speak.
3. Enter a filename (no extension — `.mp3` is added automatically).
4. Adjust **Speed** (0.5× slow → 1.0× normal → 2.0× fast). Sunbird voices ignore speed.
5. Click **Generate Audio** or press `Ctrl+Enter`.

The file appears in the right-hand list and can be downloaded or deleted.

### Batch CSV (text-to-speech)

1. Click the **Batch CSV** tab.
2. Select Language and Voice (applies to all rows).
3. Upload or drag-and-drop a `.csv` file.
4. Adjust speed if needed.
5. Click **Generate All**.

Each row is processed in sequence. A live progress list shows each file ticking off
as it completes, with a download link. Errors on individual rows are shown inline
without stopping the rest.

**CSV format** — two columns, header row optional:

```
text,filename
Welcome to our service,welcome-message
Press 1 for sales,ivr-press-1
Press 2 for support,ivr-press-2
Thank you and goodbye,goodbye
```

Limits: 500 rows maximum, 2 MB file size, 5 000 characters per text cell.

### Transcribe (speech-to-text)

1. Click the **Transcribe** tab.
2. Choose a **Backend** (Sunbird / faster-whisper / OpenAI). Backends without a
   configured token are shown as *unavailable*.
3. Pick the **spoken language**. Sunbird needs an explicit language; the Whisper
   backends also offer **Auto-detect**.
4. Upload or drag-and-drop an audio file (wav, mp3, m4a, ogg, flac, webm — up to 25 MB).
5. Optionally tick **Include per-segment timestamps**.
6. Click **Transcribe**.

The transcript appears below with **Copy** and **Save .txt** buttons.

---

## Voices

### English — Kokoro TTS (local, no API key)

| Voice ID | Name |
|---|---|
| `af_heart` | Heart — US female |
| `af_bella` | Bella — US female |
| `af_sarah` | Sarah — US female |
| `af_nicole` | Nicole — US female |
| `af_jessica` | Jessica — US female |
| `am_adam` | Adam — US male |
| `am_michael` | Michael — US male |
| `am_liam` | Liam — US male |
| `bf_emma` | Emma — GB female |
| `bf_isabella` | Isabella — GB female |
| `bm_george` | George — GB male |
| `bm_lewis` | Lewis — GB male |

### English — Sunbird AI (cloud, requires `AUTH_TOKEN`)

| Voice ID | Name |
|---|---|
| `sunbird:248` | Sunbird 248 — English female |

### Luganda — Sunbird AI (cloud, requires `AUTH_TOKEN`)

| Voice ID | Name |
|---|---|
| `sunbird:248` | Sunbird — Luganda female |

### Swahili — edge-tts (cloud, no API key)

| Voice ID | Name |
|---|---|
| `sw-KE-ZuriNeural` | Zuri — KE female |
| `sw-KE-RafikiNeural` | Rafiki — KE male |
| `sw-TZ-RehemaNeural` | Rehema — TZ female |
| `sw-TZ-DaudiNeural` | Daudi — TZ male |

---

## API

### `GET /speakers`

Returns the full TTS voice roster as JSON.

```json
{
  "English": [
    {"id": "af_heart", "name": "Heart — US female (Kokoro)"},
    ...
  ],
  "Luganda": [...],
  "Swahili": [...]
}
```

### `POST /generate`

Generate a single MP3 file.

| Field | Type | Description |
|---|---|---|
| `text` | string | Text to speak (max 5 000 chars) |
| `filename` | string | Output filename without extension |
| `language` | string | Language name from `/speakers` |
| `voice` | string | Voice ID from `/speakers` (must match language) |
| `speed` | float | Playback speed 0.5–2.0 (default 1.0) |

Response:

```json
{"filename": "welcome-message.mp3", "url": "/media/welcome-message.mp3"}
```

### `POST /batch`

Generate multiple MP3s from a CSV file, streamed as Server-Sent Events.

| Field | Type | Description |
|---|---|---|
| `file` | file | CSV upload (max 2 MB, 500 rows) |
| `language` | string | Language for all rows |
| `voice` | string | Voice for all rows |
| `speed` | float | Speed for all rows (default 1.0) |

SSE event types:

| Type | Payload |
|---|---|
| `total` | `{total: N}` |
| `start` | `{index, filename}` |
| `done` | `{index, filename, url}` |
| `error` | `{index, filename, detail}` |
| `complete` | `{}` |

### `GET /stt-backends`

Returns the STT backend roster — id → `{name, enabled, note, languages}`.
`languages` maps a language code to its display name (`auto` = detect, for the
Whisper backends).

```json
{
  "sunbird": {"name": "Sunbird AI — …", "enabled": true, "note": "", "languages": {"lug": "Luganda", ...}},
  "whisper": {"name": "faster-whisper 'base' — …", "enabled": true, "note": "Downloads the model on first use", "languages": {"auto": "Auto-detect", ...}},
  "openai":  {"name": "OpenAI Whisper API (cloud)", "enabled": false, "note": "Set OPENAI_API_KEY in .env", "languages": {...}}
}
```

### `POST /transcribe`

Transcribe an audio file.

| Field | Type | Description |
|---|---|---|
| `audio` | file | Audio upload (max 25 MB) |
| `backend` | string | `sunbird` \| `whisper` \| `openai` (default `sunbird`) |
| `language` | string | Language code valid for the backend (`auto` for the Whisper backends) |
| `timestamps` | bool | Include per-segment start/end times (default `false`) |

Response:

```json
{
  "text": "Hello, this is a test of the transcription system.",
  "language": "eng",
  "duration": 2.83,
  "segments": [{"start": 0.0, "end": 2.83, "text": "Hello, this is a test …"}],
  "backend": "sunbird"
}
```

### `GET /files`

List all generated MP3s.

```json
{"files": ["welcome-message.mp3", "ivr-press-1.mp3"]}
```

### `DELETE /files/{filename}`

Delete a file from `media/`.

### `GET /health`

```json
{"ok": true}
```

---

## How audio is produced (TTS)

```
Text input
    │
    ├─ Kokoro voice  → numpy float32 at 24 kHz → 16-bit PCM WAV
    ├─ Sunbird voice → POST api.sunbird.ai → download WAV/MP3
    └─ edge-tts voice → Microsoft neural cloud → MP3
    │
    ▼
sox → resample to mono MP3
    │
    ▼
media/<filename>.mp3   (Asterisk-compatible)
```

## How audio is transcribed (STT)

```
Audio upload  →  temp file
    │
    ├─ sunbird → POST api.sunbird.ai/tasks/audio/transcriptions (Bearer AUTH_TOKEN)
    ├─ whisper → faster-whisper WhisperModel(WHISPER_MODEL, cpu, int8), VAD filter
    └─ openai  → POST api.openai.com/v1/audio/transcriptions (whisper-1)
    │
    ▼
{ text, language, duration, segments }
```

---

## Project structure

```
Asterisk-Audio-Transcription/
├── app.py                 # FastAPI app — TTS + STT routing
├── install.py             # One-shot installer
├── requirements.txt
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── templates/
│   └── index.html         # Single-page UI (Single + Batch CSV + Transcribe tabs)
├── models/                # Kokoro model files (gitignored, downloaded by install.py)
│   ├── kokoro-v1.0.int8.onnx
│   └── voices-v1.0.bin
└── media/                 # Generated MP3 files (gitignored)
```

---

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `AUTH_TOKEN` | For Sunbird TTS voices and Sunbird STT | Sunbird AI Bearer token |
| `OPENAI_API_KEY` | For the OpenAI Whisper STT backend | OpenAI API key |
| `WHISPER_MODEL` | No (default `base`) | faster-whisper size: `tiny`, `base`, `small`, `medium`, `large-v3` |

---

## Troubleshooting

**Kokoro voices fail on startup**
```
Kokoro model files missing in models/
```
Run `python install.py` — step 5 downloads the model files.

**Sunbird returns 401**
Check that `AUTH_TOKEN` in `.env` is a valid Sunbird token and the server was restarted after editing `.env`. The same token is used for Sunbird TTS and STT.

**First transcription with faster-whisper is slow**
The model (~150 MB for `base`) downloads on first use and is then cached. Subsequent
requests reuse the in-memory model. Pick a smaller `WHISPER_MODEL` for speed or a
larger one for accuracy.

**`faster-whisper is not installed`**
Run `pip install -r requirements.txt` inside the virtualenv.

**sox cannot encode MP3 on Linux**
```bash
sudo apt install libsox-fmt-mp3
```

**edge-tts connectivity check fails**
The Microsoft neural TTS service requires internet access. If the server is behind a proxy, ensure outbound HTTPS is allowed.

**Batch CSV "Could not decode"**
Save the CSV as UTF-8 from your spreadsheet app (File → Save As → CSV UTF-8).

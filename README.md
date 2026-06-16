# Asterisk Audio Generator

A web tool for producing Asterisk-compatible **8 kHz mono MP3** audio files from text.
Supports three TTS backends selectable per generation:

| Language | Provider | Notes |
|---|---|---|
| English (12 voices) | **Kokoro TTS** | Local model — no internet, no API key |
| English (1 voice) | **Sunbird AI** | Cloud — requires `AUTH_TOKEN` |
| Luganda | **Sunbird AI** | Cloud — requires `AUTH_TOKEN` |
| Swahili (4 voices) | **edge-tts** | Microsoft neural cloud — no API key |

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

### Auth token (Sunbird voices only)

Sunbird voices (Luganda and the "Sunbird 248" English option) require a free API token.
Create an account at [api.sunbird.ai](https://api.sunbird.ai), generate a Bearer token,
then add it to `.env`:

```bash
cp .env.example .env
# edit .env and set:  AUTH_TOKEN=<your_sunbird_token>
```

English (Kokoro) and Swahili (edge-tts) voices work without any token.

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

### Single file

1. Select **Language** and **Voice** from the dropdowns.
2. Type the text to speak.
3. Enter a filename (no extension — `.mp3` is added automatically).
4. Adjust **Speed** (0.5× slow → 1.0× normal → 2.0× fast). Sunbird voices ignore speed.
5. Click **Generate Audio** or press `Ctrl+Enter`.

The file appears in the right-hand list and can be downloaded or deleted.

### Batch CSV

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

Returns the full voice roster as JSON.

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

## How audio is produced

```
Text input
    │
    ├─ Kokoro voice  → numpy float32 at 24 kHz → 16-bit PCM WAV
    ├─ Sunbird voice → POST api.sunbird.ai → download WAV
    └─ edge-tts voice → Microsoft neural cloud → MP3
    │
    ▼
sox → resample to 8 000 Hz, mono, MP3
    │
    ▼
media/<filename>.mp3   (Asterisk-compatible)
```

---

## Project structure

```
audio-generator/
├── app.py                 # FastAPI app — TTS routing, /generate, /batch, /files
├── install.py             # One-shot installer
├── requirements.txt
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── templates/
│   └── index.html         # Single-page UI (Single + Batch CSV tabs)
├── models/                # Kokoro model files (gitignored, downloaded by install.py)
│   ├── kokoro-v1.0.int8.onnx
│   └── voices-v1.0.bin
└── media/                 # Generated MP3 files (gitignored)
```

---

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `AUTH_TOKEN` | Only for Sunbird voices | Sunbird AI Bearer token |

---

## Troubleshooting

**Kokoro voices fail on startup**
```
Kokoro model files missing in models/
```
Run `python install.py` — step 5 downloads the model files.

**Sunbird returns 401**
Check that `AUTH_TOKEN` in `.env` is a valid Sunbird token and the server was restarted after editing `.env`.

**sox cannot encode MP3 on Linux**
```bash
sudo apt install libsox-fmt-mp3
```

**edge-tts connectivity check fails**
The Microsoft neural TTS service requires internet access. If the server is behind a proxy, ensure outbound HTTPS is allowed.

**Batch CSV "Could not decode"**
Save the CSV as UTF-8 from your spreadsheet app (File → Save As → CSV UTF-8).

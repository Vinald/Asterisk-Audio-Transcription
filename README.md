# HASH PDX MVP — AI Voice Assistant for IVR

End-to-end audio processing pipeline: **Speech-to-Text → Language Detection → AI Processing → Text-to-Speech**.

A caller dials a number, speaks a health question in their language, and hears an AI-generated spoken response — in real time, over a regular phone call. No smartphone, internet, or reading required.

Supports 7 East African languages. Deploys as a systemd service, Docker container, or bare Python process.

---

## Installation

Complete every step in order. Skipping any of these is the most common reason the system fails on first run.

### 1. Install system dependencies

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip sox asterisk mysql-server
```

| Package | Why |
|---|---|
| `python3` + `python3-venv` | Runs the pipeline and AGI scripts |
| `sox` | Converts audio to 8 kHz mono for Asterisk |
| `asterisk` | The PBX that handles incoming calls and runs the AGI scripts |
| `mysql-server` | Database for call records |

### 2. Provision a MySQL database

```bash
sudo mysql -u root
```

```sql
CREATE DATABASE pbx_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'pbx_user'@'localhost' IDENTIFIED BY 'strong_password';
GRANT ALL PRIVILEGES ON pbx_db.* TO 'pbx_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 3. Get a Sunbird AI API token

Create an account at [api.sunbird.ai](https://api.sunbird.ai) and generate a Bearer token. This is required for Speech-to-Text, Text-to-Speech, and language detection.

### 4. Set up your `.env` file

```bash
cp .env.example .env
nano .env
```

Fill in every variable:

| Variable | What to set |
|---|---|
| `AUTH_TOKEN` | Your Sunbird AI bearer token (from step 3) — used for STT, TTS, and language detection calls. |
| `API_TOKEN` | Bearer token for the local `/api/v1/` REST API — used by Asterisk AGI scripts to authenticate to the pipeline. Generate with `python3 -c "import secrets; print(secrets.token_hex(32))"`. |
| `DATABASE_URL` | `mysql+pymysql://pbx_user:strong_password@localhost:3306/pbx_db` |
| `SERVER_PUBLIC_IP` | Your server's public IP — run `curl -s ifconfig.me` to find it |
| `HASHIE_CHAT_URL` | Hashie MedGemma endpoint (default is pre-filled) |
| `DASHBOARD_USERNAME` | Login username for the web dashboard |
| `DASHBOARD_PASSWORD` | Login password for the web dashboard |
| `DASHBOARD_SECRET_KEY` | Secret used to sign session cookies — generate with `python3 -c "import secrets; print(secrets.token_hex(32))"` |

> `SERVER_PUBLIC_IP` is written into Asterisk's `pjsip.conf` by the installer. Without it, calls connect but there is **no audio**.

### 5. Open firewall ports

```bash
sudo ufw allow 22/tcp           # SSH — do this first to avoid lockout
sudo ufw allow 5060/udp         # SIP signaling
sudo ufw allow 5060/tcp
sudo ufw allow 10000:20000/udp  # RTP audio
sudo ufw allow 8000/tcp         # Pipeline API
sudo ufw --force enable
sudo ufw status
```

| Port | Protocol | Purpose |
|---|---|---|
| 5060 | UDP + TCP | SIP signaling (phone registration & call setup) |
| 10000–20000 | UDP | RTP audio (the actual voice stream) |
| 8000 | TCP | Pipeline REST API |

> If your server is behind a cloud firewall (AWS Security Groups, GCP Firewall Rules, etc.), add the same rules there in addition to `ufw`.

### 6. Generate the IVR audio prompt files

The IVR plays 19 pre-recorded audio prompts (greetings, menus, instructions). They must be generated before the installer can copy them to Asterisk.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/generate_media.py
```

This creates `media/hash-*.wav` — 8 kHz mono WAV files ready for Asterisk. The script is safe to re-run; it skips files that already exist. Use `--force` to regenerate everything.

| File | Prompt text |
|---|---|
| `hash-greeting` | "Hello friend! Welcome to the HASH conversational agent" |
| `hash-language-menu` | "…press 1 for English, press 2 for Luganda" |
| `hash-welcome-english` | English welcome with language confirmation |
| `hash-welcome-luganda` | Luganda welcome with language confirmation |
| `hash-question-prompt-english` | "Do you have a health question? Press 1 Yes, Press 2 No" |
| `hash-question-prompt-luganda` | Luganda version |
| `hash-ask-q1-english` | "After the beep, please ask your first question" |
| `hash-ask-q1-luganda` | Luganda version |
| `hash-processing-english` | "The agent is processing your request. Please wait." |
| `hash-processing-luganda` | Luganda version |
| `hash-ask-q2-english` | "After the beep, please ask your second question" |
| `hash-ask-q2-luganda` | Luganda version |
| `hash-goodbye-english` | "Thank you for your questions. Goodbye friend, stay well." |
| `hash-goodbye-luganda` | Luganda version |
| `hash-invalid-lang` | Invalid language selection (English, pre-selection) |
| `hash-invalid-choice-english` | Invalid yes/no selection (English) |
| `hash-invalid-choice-luganda` | Invalid yes/no selection (Luganda) |
| `hash-error-english` | AGI processing error (English) |
| `hash-error-luganda` | AGI processing error (Luganda) |

### 7. Run the installer

```bash
sudo bash install.sh
```

The installer handles everything else: Python venv, pip dependencies, database migrations, AGI scripts, Asterisk config (with your public IP stamped in), audio prompts copied to Asterisk sounds, and the systemd service.

Verify it worked:

```bash
curl http://localhost:8000/api/v1/health
sudo systemctl status stt-tts-pipeline
```

---

## How It Works

A caller dials extension 8446. The call is handled by Asterisk PBX, which records audio and passes it to the pipeline through AGI scripts.

```
You pick up the phone
         │
         ▼
Dial the number (8446)
         │
         ▼
Hear a greeting + language menu
"Press 1 for English, Press 2 for Luganda"
         │
         ▼
Hear a welcome in your chosen language
         │
         ▼
"Do you have a health question? Press 1 Yes, Press 2 No"
         │
    ┌────┴────┐
   No        Yes
    │         │
 Goodbye      ▼
         "After the beep, ask your first question"
         │
         ▼
You speak (recorded up to 10 s, stops after 3 s silence)
         │
         ▼
"The agent is processing your request. Please wait."
[music on hold]
         │
         ▼
AI response played back in your language
         │
         ▼
Second question — same flow repeats
         │
         ▼
Goodbye / call ends
```

Each time the caller speaks, four things happen in sequence:

1. **Speech → Text** — the voice recording is sent to Sunbird AI, which transcribes it (African language specialist)
2. **Language Detection** — the language is identified automatically (`eng`, `lug`, `swa`, …)
3. **AI Response** — the question is sent to Hashie MedGemma, a medical AI built for the Ugandan health context
4. **Text → Speech** — the AI's answer is converted back to spoken audio in the caller's language and played back

```
Caller's voice
     │
     ▼
[ Speech → Text ]      ──  "I have a fever and a headache"
     │
     ▼
[ Language Detection ] ──  "This is English"
     │
     ▼
[ Hashie AI ]          ──  "You may want to rest, stay hydrated,
     │                      and visit a clinic if symptoms persist..."
     ▼
[ Text → Speech ]      ──  spoken response played to caller
```

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Caller (SIP Phone)                         │
│                         dials ext. 8446                             │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ SIP / PJSIP
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Asterisk PBX                                 │
│  extensions.conf  ─── dialplan (context: ivr)                       │
│  pjsip.conf       ─── endpoint registration                         │
│                                                                     │
│  1. Answer + beep + greeting                                        │
│  2. Language menu → press 1 (English) or 2 (Luganda)               │
│  3. save_language.py  — persist language choice to DB               │
│  4. "Do you have a question?" → press 1 Yes / 2 No                 │
│     No/timeout → log_no_question.py → goodbye                      │
│  5. Record Q1 → /tmp/input-{CALLID}-1.wav (10 s max, 3 s silence)  │
│  6. ai_assistant.py   — Q1: STT → AI → TTS → playback              │
│  7. Record Q2 → /tmp/input-{CALLID}-2.wav (10 s max, 3 s silence)  │
│  8. ai_assistant.py   — Q2: STT → AI → TTS → playback              │
│  9. Goodbye → Hangup                                                │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ AGI (Python script over stdin/stdout)
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│              AGI Script  (asterisk/ai_assistant.py)                 │
│                                                                     │
│  • Reads AGI env (caller ID, extension, unique call ID)             │
│  • Validates & chmod 777 the recorded WAV file                      │
│  • POST /tmp/input-{CALLID}-N.wav → localhost:8000/api/v1/pipeline  │
│  • Receives JSON result (text + audio URL)                          │
│  • Downloads audio URL → /tmp/ai_response_{call_id}_{qnum}.wav      │
│  • Converts to 8 kHz mono PCM with sox (Asterisk format)            │
│  • Sets AGI channel variable AI_RESPONSE_FILE → dialplan plays it   │
│  • Writes Q1/Q2 row to MySQL calls table                            │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTP POST multipart/form-data
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│           Pipeline API  (app/main.py — FastAPI on :8000)            │
│                                                                     │
│  POST /api/v1/pipeline                                              │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  Step 1 — Speech-to-Text (STT)                              │    │
│  │  POST api.sunbird.ai/tasks/modal/stt                        │    │
│  └──────────────────────────┬──────────────────────────────────┘    │
│  ┌──────────────────────────▼──────────────────────────────────┐    │
│  │  Step 2 — Language Detection                                │    │
│  │  POST api.sunbird.ai/tasks/language_id                      │    │
│  └──────────────────────────┬──────────────────────────────────┘    │
│  ┌──────────────────────────▼──────────────────────────────────┐    │
│  │  Step 3 — AI Agent (Hashie MedGemma)                        │    │
│  │  POST hashie-medgemma…modal.run/chat                        │    │
│  └──────────────────────────┬──────────────────────────────────┘    │
│  ┌──────────────────────────▼──────────────────────────────────┐    │
│  │  Step 4 — Text-to-Speech (TTS)                              │    │
│  │  POST api.sunbird.ai/tasks/modal/tts                        │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  Response: { input_text, output_text, detected_language,            │
│              output_audio_url, timing, speaker_id }                 │
└─────────────────────────────────────────────────────────────────────┘
```

## Call Flow (Sequence)

```
Caller        Asterisk           AGI Script        Pipeline API       Sunbird / Hashie
  │               │                   │                   │                    │
  │── dial 8446 ─▶│                   │                   │                    │
  │◀─ welcome ────│                   │                   │                    │
  │── press 1 ────│                   │                   │                    │
  │               │── save_language ─▶│                   │                    │
  │◀─ "Ask Q1" ───│                   │                   │                    │
  │── (speaks) ───│                   │                   │                    │
  │               │ record WAV        │                   │                    │
  │               │── ai_assistant ──▶│                   │                    │
  │               │                   │── POST /api/v1/pipeline ──▶│               │
  │               │                   │                   │── STT ────────────▶│
  │               │                   │                   │◀─ text ────────────│
  │               │                   │                   │── lang detect ────▶│
  │               │                   │                   │◀─ lang code ───────│
  │               │                   │                   │── Hashie chat ────▶│
  │               │                   │                   │◀─ AI response ─────│
  │               │                   │                   │── TTS ────────────▶│
  │               │                   │                   │◀─ audio URL ───────│
  │               │                   │◀─ JSON result ─── │                    │
  │               │                   │ download + sox    │                    │
  │               │◀─ AI_RESPONSE_FILE│                   │                    │
  │◀─ play audio ─│                   │                   │                    │
  │   (repeat Q2) │                   │                   │                    │
  │◀─ goodbye ────│                   │                   │                    │
```

## Features

- **Complete Pipeline**: Audio → STT → Language Detection → AI Agent → TTS → Audio
- **7 East African Languages**: `eng`, `lug`, `ach`, `teo`, `nyn`, `lgg`, `swa`
- **Auto Language Detection**: No button press required — detects language from speech
- **Multi-Question Support**: One DB row per call storing both Q1 and Q2 exchanges
- **Performance Tracking**: Per-stage timing (STT, agent, TTS) stored in a separate `call_metrics` table, keyed by `(call_id, question_number)`
- **FastAPI REST API**: Async, auto-documented at `/docs`
- **Alembic Migrations**: Version-controlled database schema
- **Asterisk AGI Integration**: PBX dialplan triggers the pipeline via AGI scripts
- **Heartbeat Daemon**: Background thread keeps Sunbird API endpoints warm
- **Systemd Service**: Auto-start on boot, journal logging
- **Docker Support**: Container deployment via `docker-compose`

## Supported Languages

| Language | Code | TTS Speaker ID |
| --- | --- | --- |
| English | `eng` | 248 |
| Luganda | `lug` | 248 (female) |
| Acholi | `ach` | 241 (female) |
| Ateso | `teo` | 242 (female) |
| Runyankore | `nyn` | 243 (female) |
| Lugbara | `lgg` | 245 (female) |
| Swahili | `swa` | 246 (male) |

## External Services

| Service | Endpoint | Purpose |
| --- | --- | --- |
| Sunbird STT | `api.sunbird.ai/tasks/modal/stt` | Speech → text (African languages) |
| Sunbird Language ID | `api.sunbird.ai/tasks/language_id` | Detect language from transcribed text |
| Sunbird TTS | `api.sunbird.ai/tasks/modal/tts` | Text → speech (per-language voice) |
| Hashie MedGemma | `sb-modal-ws--hashie-medgemma…modal.run` | Medical AI chat (Uganda context) |

All Sunbird calls use Bearer token auth with exponential-backoff retry (up to 5 attempts). The heartbeat daemon pings all three Sunbird endpoints every 60 seconds to prevent serverless cold starts.

## Project Structure

```text
hash-pbx/
├── app/
│   ├── main.py              # FastAPI entry point — lifespan, middleware, router mounts
│   ├── heartbeat.py         # Background daemon to keep Sunbird API endpoints warm
│   ├── core/
│   │   ├── config.py        # Settings class — single source of truth for all env vars
│   │   ├── database.py      # SQLAlchemy engine, SessionLocal, Base — schema via Alembic
│   │   ├── middleware.py    # DocsAuthMiddleware — protects /docs, /redoc, /openapi.json
│   │   └── security.py      # is_authenticated(), require_auth(), verify_credentials(), verify_api_token()
│   ├── models/              # SQLAlchemy ORM table definitions
│   │   ├── call.py
│   │   ├── call_metrics.py
│   │   ├── caller_preferences.py
│   │   ├── cdr.py
│   │   └── system_log.py
│   ├── schemas/             # Pydantic v2 request/response shapes
│   │   ├── call.py
│   │   ├── call_metrics.py
│   │   ├── caller_preferences.py
│   │   ├── cdr.py
│   │   └── system_log.py
│   ├── services/            # Business logic layer
│   │   ├── agent.py         # Hashie AI agent wrapper
│   │   ├── events.py        # Structured system log writer
│   │   ├── history.py       # All DB read/write operations (calls, metrics, CDR, logs, prefs)
│   │   ├── pipeline.py      # End-to-end audio pipeline orchestration
│   │   ├── stt.py           # Speech-to-text + language detection
│   │   └── tts.py           # Text-to-speech + speaker resolution
│   ├── clients/             # Low-level HTTP clients for external APIs
│   │   ├── sunbird.py       # Sunbird AI STT, TTS, language-ID calls
│   │   └── _retry.py        # Exponential-backoff retry decorator
│   ├── api/
│   │   ├── docs.py          # Protected /docs, /redoc, /openapi.json routes
│   │   ├── rest/
│   │   │   └── v1/
│   │   │       └── endpoints/   # REST API routers — one file per resource
│   │   │           ├── health.py      # GET  /api/v1/health
│   │   │           ├── stt.py         # POST /api/v1/stt, /api/v1/stt/language-detect
│   │   │           ├── tts.py         # POST /api/v1/tts
│   │   │           ├── agent.py       # POST /api/v1/agent
│   │   │           ├── pipeline.py    # POST /api/v1/pipeline
│   │   │           ├── speakers.py    # GET  /api/v1/speakers
│   │   │           ├── history.py     # GET/POST /api/v1/history
│   │   │           ├── metrics.py     # GET/POST /api/v1/metrics
│   │   │           ├── preferences.py # GET/PUT  /api/v1/preferences
│   │   │           ├── cdr.py         # GET/POST /api/v1/cdr
│   │   │           └── logs.py        # GET/POST /api/v1/logs
│   │   └── dashboard/
│   │       └── endpoints/   # Session-authenticated HTML dashboard routers
│   │           ├── auth.py        # GET/POST /login, GET /logout
│   │           ├── overview.py    # GET /dashboard
│   │           ├── calls.py       # GET /dashboard/calls, /dashboard/calls/{call_id}
│   │           ├── logs.py        # GET /dashboard/logs
│   │           ├── metrics.py     # GET /dashboard/metrics
│   │           └── exports.py     # GET /export/calls.csv, /export/cdr.csv, /export/metrics.csv
│   └── templates/           # Jinja2 HTML templates for the dashboard
│       ├── base.html        # Sidebar layout + dark/light mode toggle
│       ├── login.html       # Login page
│       ├── dashboard.html   # Overview stats
│       ├── calls.html       # Paginated calls table with filters
│       ├── call_detail.html # Single call detail with Q1/Q2 and metrics
│       ├── metrics.html     # Call metrics table
│       ├── logs.html        # System log viewer
│       ├── index.html       # Landing page (redirects to dashboard if logged in)
│       └── error.html       # Error page (404, etc.)
├── scripts/
│   ├── migrate_db.py        # Apply Alembic migrations
│   ├── reset_db.py          # Truncate all tables for a fresh start (interactive)
│   ├── generate_media.py    # Generate IVR audio prompts via Sunbird TTS
│   └── diagnose.py          # Connectivity diagnostic tool
├── alembic/
│   └── versions/
│       ├── 001_initial.py      # Base schema (calls, caller_preferences, asterisk_cdr, system_log)
│       └── 002_call_metrics.py # call_metrics table; timing/URL columns moved out of calls
├── asterisk/
│   ├── agi_lib/
│   │   ├── agi_io.py    # AGI I/O primitives (send, recv, set_variable, verbose, read_env)
│   │   ├── config.py    # Load .env, parse DATABASE_URL
│   │   ├── db.py        # Direct MySQL operations for AGI scripts
│   │   ├── audio.py     # Download + sox conversion for Asterisk playback
│   │   └── pipeline.py  # HTTP client for localhost:8000/api/v1/pipeline
│   ├── ai_assistant.py      # Q1/Q2: validate → pipeline → download → save → playback
│   ├── save_language.py     # Upsert caller_preferences + update calls.language
│   ├── log_no_question.py   # Log calls where caller pressed No / timed out
│   ├── extensions.conf      # Asterisk dialplan (5 contexts, full IVR flow)
│   └── pjsip.conf           # SIP endpoint config
├── tests/
│   ├── conftest.py          # Shared fixtures (TestClient, SQLite DB, sample data)
│   ├── test_api.py          # REST API endpoints — all /api/v1/* routes
│   ├── test_auth.py         # Login, logout, session, access control
│   ├── test_routes.py       # Dashboard pages, pagination, filters, edge cases
│   ├── test_exports.py      # CSV export auth and format
│   └── test_unit.py         # Pure unit tests (_caller_colors, resolve_language, DB round-trips)
├── .env.example
├── alembic.ini
├── Dockerfile
├── docker-compose.yml
├── install.sh               # One-shot installer (run this after creating .env)
├── requirements.txt
└── stt-tts-pipeline.service # systemd unit template (install.sh writes the live copy)
```

## Database Migrations

Schema is managed with [Alembic](https://alembic.sqlalchemy.org/). Always run migrations before starting the app for the first time, and after pulling changes that include new migration files.

```bash
source .venv/bin/activate
alembic upgrade head
```

`install.sh` runs this automatically. For subsequent schema changes, create a new migration:

```bash
alembic revision --autogenerate -m "describe_your_change"
alembic upgrade head
```

To check the current state of the database:

```bash
alembic current   # which migration is applied
alembic history   # full migration history
```

> Never use `Base.metadata.create_all()` directly in production — it bypasses Alembic's version tracking and will diverge from the migration history.

---

## Running

### Direct Python

```bash
source .venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Docker Compose

```bash
docker-compose up -d
docker-compose logs -f
```

## Tests

Tests use SQLite — no MySQL instance required. Run them after activating the venv:

```bash
source .venv/bin/activate
pip install -r requirements.txt   # if not already installed
pytest tests/ -v
```

| File | What it covers |
| --- | --- |
| `tests/test_api.py` | All `/api/v1/` REST endpoints — CRUD, 404s, 422 validation, bearer token enforcement |
| `tests/test_auth.py` | Login, wrong credentials, logout, session expiry, access control on all protected routes |
| `tests/test_routes.py` | All dashboard pages, pagination edge cases (page 0, negative, beyond total), invalid date filters, 404 for missing call |
| `tests/test_exports.py` | CSV exports — auth-gated, correct headers, no `"None"` strings for null fields |
| `tests/test_unit.py` | `_caller_colors`, `resolve_language`, `validate_audio`, `speaker_for`, DB round-trips |

Run a single file or test:

```bash
pytest tests/test_auth.py -v
pytest tests/test_unit.py::TestCallerColors -v
```

## Web Dashboard

A session-authenticated dashboard is served alongside the API at port 8000.

| URL | Description |
| --- | --- |
| `/dashboard` | Overview — total calls, language/status breakdown, avg processing times, recent calls |
| `/dashboard/calls` | Paginated calls table with filters (status, language, date range); shows Call ID, Caller, Language, Status, Q1/Q2 question and answer (truncated — hover for full text, click row to open detail) |
| `/dashboard/calls/{call_id}` | Single call detail — Q1/Q2 transcripts, AI responses, per-stage timings |
| `/dashboard/metrics` | Call metrics table (STT, agent, TTS, total duration per question) |
| `/dashboard/logs` | System log viewer with level filter |
| `/export/calls.csv` | Download all calls as CSV |
| `/export/cdr.csv` | Download CDR as CSV |
| `/export/metrics.csv` | Download call metrics as CSV |

**Rows with the same caller are colour-coded** across all tables for easy visual grouping. The dashboard defaults to dark mode with a light/dark toggle that persists across sessions.

### Access

Navigate to `http://your-server:8000/dashboard` and sign in with the credentials set in `.env` (`DASHBOARD_USERNAME` / `DASHBOARD_PASSWORD`).

### Dependencies

The dashboard requires `jinja2` and `itsdangerous` — both are listed in `requirements.txt` and installed automatically by `install.sh`.

---

## API Endpoints

All REST endpoints are versioned under `/api/v1`.

| Endpoint | Method | Auth | Description |
| --- | --- | --- | --- |
| `/api/v1/health` | GET | None | Service health + Sunbird endpoint status |
| `/api/v1/pipeline` | POST | Bearer | Full pipeline: audio in → audio URL out |
| `/api/v1/stt` | POST | Bearer | Speech-to-Text only |
| `/api/v1/tts` | POST | Bearer | Text-to-Speech only |
| `/api/v1/stt/language-detect` | POST | Bearer | Language detection only |
| `/api/v1/agent` | POST | Bearer | Hashie AI agent only |
| `/api/v1/speakers` | GET | Bearer | Available TTS speaker IDs per language |
| `/api/v1/history` | GET | Bearer | Call history (paginated) |
| `/api/v1/history` | POST | Bearer | Create a call record |
| `/api/v1/history/stats` | GET | Bearer | Aggregate call statistics |
| `/api/v1/history/{call_id}` | GET | Bearer | Single call detail |
| `/api/v1/metrics` | POST | Bearer | Record pipeline timing metrics |
| `/api/v1/metrics/{call_id}` | GET | Bearer | Metrics for a specific call |
| `/api/v1/preferences` | GET | Bearer | List all caller language preferences |
| `/api/v1/preferences/{caller_id}` | GET | Bearer | Preference for a specific caller |
| `/api/v1/preferences/{caller_id}` | PUT | Bearer | Set caller language preference |
| `/api/v1/cdr` | GET | Bearer | List Asterisk CDR records (paginated) |
| `/api/v1/cdr` | POST | Bearer | Insert a CDR record |
| `/api/v1/cdr/{uniqueid}` | GET | Bearer | Single CDR record |
| `/api/v1/logs` | GET | Bearer | List system log entries (paginated, filterable) |
| `/api/v1/logs` | POST | Bearer | Write a system log entry |
| `/docs` | GET | Session | Auto-generated Swagger UI (requires dashboard login) |
| `/redoc` | GET | Session | ReDoc API docs (requires dashboard login) |

### Authentication

All `/api/v1/` endpoints except `/api/v1/health` require a bearer token:

```
Authorization: Bearer <AUTH_TOKEN>
```

`API_TOKEN` is a separate secret from `AUTH_TOKEN` (the Sunbird credential). Set it in `.env`. The `/api/v1/health` endpoint is intentionally exempt so the Docker healthcheck and monitoring tools can reach it without credentials.

Requests without the header (or with a wrong token) receive `HTTP 401 Unauthorized`.

### Examples

```bash
export TOKEN="your-api-token-here"   # value of API_TOKEN in .env

# Health check — no auth required
curl http://localhost:8000/api/v1/health

# All other endpoints require the bearer token
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/speakers
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/history
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/history/stats
curl -H "Authorization: Bearer $TOKEN" \
  -F "audio=@audio.wav" http://localhost:8000/api/v1/pipeline
curl -H "Authorization: Bearer $TOKEN" \
  -F "audio=@audio.wav" http://localhost:8000/api/v1/stt
curl -H "Authorization: Bearer $TOKEN" \
  -F "text=Hello" -F "language=eng" http://localhost:8000/api/v1/tts
curl -H "Authorization: Bearer $TOKEN" \
  -F "text=Oli otya" http://localhost:8000/api/v1/stt/language-detect
```

## Database Schema

All tables live in the single MySQL database specified by `DATABASE_URL`.

### calls

One row per phone call. Written by `ai_assistant.py` — Q1 columns on first AGI run, Q2 columns updated on second. Timing and audio URLs are stored in `call_metrics` (see below).

| Column | Type | Notes |
| --- | --- | --- |
| call_id | VARCHAR(255) | UNIQUE — format `HASH-YYYYMMDD-HHMMSS-N` (e.g. `HASH-20260611-041203-0`) |
| caller_id | VARCHAR(50) | Caller number |
| extension | VARCHAR(20) | Dialled extension |
| language | VARCHAR(50) | Language chosen by caller (`English` or `Luganda`) |
| speaker_id | Integer | TTS speaker used |
| status | VARCHAR(50) | `in_progress` → `completed` \| `error_q1` \| `error_q2` \| `no_question` \| `timeout` \| `lang_timeout` |
| q1_input_text | Text | User's first question (transcribed) |
| q1_output_text | Text | AI response to Q1 |
| q1_detected_language | VARCHAR(50) | Full language name detected for Q1 (e.g. `English`, `Luganda`, `Acholi`) |
| q1_input_audio | VARCHAR(500) | Input audio filename |
| q2_* | — | Same content fields for Q2 (no timing/URL — those go to `call_metrics`) |

### call_metrics

One row per question per call. Stores performance data and TTS audio URLs separately so the `calls` table stays focused on conversation content.

| Column | Type | Notes |
| --- | --- | --- |
| id | Integer | Auto-increment PK |
| call_id | VARCHAR(255) | FK → calls.call_id |
| question_number | Integer | `1` or `2` |
| audio_url | VARCHAR(2000) | GCS signed URL for the TTS response audio |
| stt_duration | Float | Speech-to-Text time (s) |
| agent_duration | Float | AI agent time (s) |
| tts_duration | Float | Text-to-Speech time (s) |
| total_duration | Float | End-to-end pipeline time (s) |

### caller_preferences

Written by `save_language.py` when a caller selects their language.

| Column | Type | Notes |
| --- | --- | --- |
| caller_id | VARCHAR(50) | UNIQUE — caller number |
| language | VARCHAR(50) | Full language name e.g. `English`, `Luganda` |
| updated_at | DateTime | Auto-updated on each call |

### asterisk_cdr

Written at the end of every answered call:
- `ai_assistant.py` writes it after Q2 completes (or on AGI error)
- `log_no_question.py` writes it when the caller declines to ask / times out

| Column | Type | Notes |
| --- | --- | --- |
| uniqueid | VARCHAR(255) | UNIQUE — Asterisk UNIQUEID |
| call_id | VARCHAR(255) | FK → calls |
| src / dst | VARCHAR(50) | Caller / called number |
| duration | Integer | Call duration in seconds |
| disposition | VARCHAR(50) | `ANSWERED`, `NO ANSWER`, `BUSY`, `FAILED` |

### system_log

Written by all AGI scripts and the `/pipeline` API endpoint.

| Column | Type | Notes |
| --- | --- | --- |
| level | VARCHAR(20) | `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| component | VARCHAR(50) | `agi`, `pipeline` |
| event_type | VARCHAR(100) | `agi_complete`, `agi_error`, `call_no_question`, `pipeline_complete`, `pipeline_error` |
| message | Text | Event message |
| call_id | VARCHAR(255) | FK → calls — present for all entries including pipeline logs |

## Docker

```bash
docker build -t stt-tts-pipeline:latest .
docker run --env-file .env -p 8000:8000 stt-tts-pipeline:latest
```

## Systemd Service Commands

```bash
sudo systemctl start stt-tts-pipeline
sudo systemctl stop stt-tts-pipeline
sudo systemctl restart stt-tts-pipeline
sudo systemctl enable stt-tts-pipeline
sudo journalctl -u stt-tts-pipeline -f
```

## Asterisk Integration

AGI scripts and Asterisk config files are installed automatically by `install.sh`.

The installer copies:

- `asterisk/ai_assistant.py`, `save_language.py`, `log_no_question.py` → `/usr/share/asterisk/agi-bin/`
- `asterisk/agi_lib/` → `/usr/share/asterisk/agi-bin/agi_lib/`
- `asterisk/pjsip.conf` → `/etc/asterisk/pjsip.conf` (existing file backed up with timestamp)
- `asterisk/extensions.conf` → `/etc/asterisk/extensions.conf` (existing file backed up with timestamp)
- `media/hash-*.wav` → `/var/lib/asterisk/sounds/` and `/var/lib/asterisk/sounds/en/`

The repo is the single source of truth for both config files. Re-running `install.sh` after any change will back up and replace both.

`agi_lib/config.py` reads `DATABASE_URL` from the project `.env` using the `STT_TTS_PROJECT_DIR` environment variable set in `/etc/environment` by the installer.

`agi_lib/pipeline.py` reads `AUTH_TOKEN` from the Asterisk process environment to authenticate its HTTP calls to `/api/v1/pipeline`. The installer must expose `AUTH_TOKEN` to the Asterisk systemd unit — verify it is present in `/etc/systemd/system/asterisk.service.d/hash-env.conf`:

```ini
[Service]
Environment="API_TOKEN=your-api-token-here"
```

If this is missing, every call will fail with a 401 and the caller will hear the error prompt.

Dialplan entry point:

```ini
exten => 8446,1,NoOp(HASH AI call)
 same => n,Set(CALLID=${STRFTIME(${EPOCH},,HASH-%Y%m%d-%H%M%S)}-${CUT(UNIQUEID,.,2)})
 same => n,Answer()
 ...
 same => n,AGI(ai_assistant.py,/tmp/input-${CALLID}-1.wav,1,${LANGUAGE},${CALLID})
```

The `CALLID` variable embeds the date, time, and Asterisk sequence number — for example `HASH-20260611-041203-0` — making call records human-readable without sacrificing uniqueness.

## Diagnostics

```bash
python scripts/diagnose.py
```

Checks `AUTH_TOKEN`, local API health, and Sunbird endpoint reachability.

## Troubleshooting

```bash
# Service logs
sudo journalctl -u stt-tts-pipeline -f

# API debug mode
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level debug

# Database
sudo systemctl status mysql
mysql -u root -p pbx_db -e "SHOW TABLES;"

# Port conflict
fuser -k 8000/tcp && sudo systemctl restart stt-tts-pipeline

# Port check
netstat -tlnp | grep 8000
```

## Security

- Store all credentials in `.env` — never commit it to Git
- Use strong, unique database passwords
- `AUTH_TOKEN` (Sunbird) and `API_TOKEN` (local API) are separate secrets — rotate them independently
- Rotating `API_TOKEN` requires updating the Asterisk systemd env (`hash-env.conf`) and reloading the service
- Deploy behind HTTPS (nginx/caddy reverse proxy)
- Restrict firewall access to port 8000
- `/api/v1/health` is intentionally unauthenticated — do not store sensitive data in its response
- Dashboard session cookies are signed with `DASHBOARD_SECRET_KEY`; use a random 32-byte hex value in production (`python3 -c "import secrets; print(secrets.token_hex(32))"`)
- All token comparisons use `secrets.compare_digest` to prevent timing attacks

## Resources

- [Sunbird AI API](https://api.sunbird.ai/docs)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Asterisk AGI](https://docs.asterisk.org/Configuration/Interfaces/Asterisk-Gateway-Interface-AGI/)
- [Alembic](https://alembic.sqlalchemy.org/)
- [Docker](https://docs.docker.com/)

#!/bin/bash
# One-shot installer for STT-TTS Pipeline.
# Run after creating your .env file: sudo bash install.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok()   { echo -e "${GREEN}✓ $*${NC}"; }
warn() { echo -e "${YELLOW}[!] $*${NC}"; }
die()  { echo -e "${RED}[!] $* — aborting${NC}"; exit 1; }

PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SERVICE_NAME="stt-tts-pipeline"

echo "============================================"
echo " STT-TTS Pipeline — Installer"
echo " Project: $PROJECT_DIR"
echo "============================================"
echo ""

[ "$EUID" -ne 0 ] && die "Please run as root: sudo bash install.sh"

PROJECT_USER=$(ls -ld "$PROJECT_DIR" | awk '{print $3}')
echo "[*] Running as root, service will run as: $PROJECT_USER"

# ── 1. Check .env ──────────────────────────────────────────────────
echo ""
echo "=== Step 1: Environment ==="

if [ ! -f "$PROJECT_DIR/.env" ]; then
    if [ -f "$PROJECT_DIR/.env.example" ]; then
        cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
        warn ".env created from template — edit $PROJECT_DIR/.env and set AUTH_TOKEN + DATABASE_URL, then re-run."
        exit 1
    else
        die ".env not found. Copy .env.example to .env and fill in your credentials."
    fi
fi

# Bail early if AUTH_TOKEN is still a placeholder
AUTH_TOKEN_VALUE=$(grep -E '^AUTH_TOKEN=' "$PROJECT_DIR/.env" | cut -d= -f2-)
if [ -z "$AUTH_TOKEN_VALUE" ] || echo "$AUTH_TOKEN_VALUE" | grep -qi "your_.*token\|placeholder"; then
    die "AUTH_TOKEN in .env looks like a placeholder. Set a real token and re-run."
fi

# Read SERVER_PUBLIC_IP from .env
SERVER_PUBLIC_IP=$(grep -E '^SERVER_PUBLIC_IP=' "$PROJECT_DIR/.env" | cut -d= -f2-)
if [ -z "$SERVER_PUBLIC_IP" ] || echo "$SERVER_PUBLIC_IP" | grep -qi "YOUR_SERVER"; then
    warn "SERVER_PUBLIC_IP not set in .env — pjsip.conf will use placeholder IP"
    warn "Set SERVER_PUBLIC_IP=<your public IP> in .env for correct SIP/RTP routing"
else
    ok "SERVER_PUBLIC_IP=$SERVER_PUBLIC_IP"
fi

ok ".env found and AUTH_TOKEN is set"

# ── 2. Python venv + dependencies ─────────────────────────────────
echo ""
echo "=== Step 2: Python Dependencies ==="

if [ ! -d "$PROJECT_DIR/.venv" ]; then
    echo "[*] Creating virtual environment..."
    python3 -m venv "$PROJECT_DIR/.venv"
fi

PYTHON="$PROJECT_DIR/.venv/bin/python"
PIP="$PROJECT_DIR/.venv/bin/pip"

echo "[*] Installing packages..."
"$PIP" install --upgrade pip setuptools wheel -q
"$PIP" install -r "$PROJECT_DIR/requirements.txt" -q
ok "Python dependencies installed"

# ── 3. Database migrations ─────────────────────────────────────────
echo ""
echo "=== Step 3: Database Migrations ==="

echo "[*] Running Alembic migrations..."
cd "$PROJECT_DIR"
"$PYTHON" scripts/migrate_db.py || die "Migration failed. Check DATABASE_URL in .env and ensure MySQL is running."
ok "Database migrations applied"

# ── 4. Verify database tables ─────────────────────────────────────
echo ""
echo "=== Step 4: Verifying Database Tables ==="

DOTENV="$PROJECT_DIR/.env" "$PYTHON" - << 'PYEOF'
import os, sys
from dotenv import load_dotenv
load_dotenv(os.environ["DOTENV"])
try:
    from app.core.database import engine
    from sqlalchemy import inspect
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())
    required = {"calls", "call_metrics", "caller_preferences", "asterisk_cdr", "system_log"}
    missing  = required - existing
    for t in sorted(required):
        mark = "✓" if t in existing else "✗"
        print(f"  [{mark}] {t}")
    if missing:
        print(f"\n[!] Missing tables: {', '.join(sorted(missing))}")
        sys.exit(1)
    print("\n✓ All required tables present")
except Exception as e:
    print(f"[!] DB check failed: {e}")
    sys.exit(1)
PYEOF
[ $? -eq 0 ] && ok "Database tables verified" || die "Database verification failed — check migrations."

# ── 6. Asterisk AGI files ──────────────────────────────────────────
echo ""
echo "=== Step 5: Asterisk AGI Scripts ==="

AGI_BIN="/var/lib/asterisk/agi-bin"
AGI_SRC="$PROJECT_DIR/asterisk"

if [ ! -d "$AGI_BIN" ]; then
    echo "[*] Creating $AGI_BIN ..."
    mkdir -p "$AGI_BIN"
    if id asterisk &>/dev/null; then
        chown asterisk:asterisk "$AGI_BIN"
    fi
    ok "Created $AGI_BIN"
fi

if [ -d "$AGI_BIN" ]; then
    echo "[*] Copying AGI scripts to $AGI_BIN ..."
    cp "$AGI_SRC/ai_assistant.py"   "$AGI_BIN/"
    cp "$AGI_SRC/save_language.py"  "$AGI_BIN/"
    cp "$AGI_SRC/log_no_question.py" "$AGI_BIN/"

    chmod +x "$AGI_BIN/ai_assistant.py" "$AGI_BIN/save_language.py" "$AGI_BIN/log_no_question.py"

    # Copy shared library package
    rm -rf "$AGI_BIN/agi_lib"
    cp -r "$AGI_SRC/agi_lib" "$AGI_BIN/"

    # Set ownership to asterisk user if it exists
    if id asterisk &>/dev/null; then
        chown -R asterisk:asterisk \
            "$AGI_BIN/ai_assistant.py" \
            "$AGI_BIN/save_language.py" \
            "$AGI_BIN/log_no_question.py" \
            "$AGI_BIN/agi_lib"
    fi
    ok "AGI scripts installed to $AGI_BIN"

    # ── AGI Python dependencies ────────────────────────────────────────
    # Install into /var/lib/asterisk/python-libs so the asterisk user can
    # always import them regardless of home-directory traverse permissions.
    AGI_PYLIBS="/var/lib/asterisk/python-libs"
    echo "[*] Installing AGI Python dependencies to $AGI_PYLIBS ..."
    mkdir -p "$AGI_PYLIBS"
    pip3 install --quiet --target "$AGI_PYLIBS" requests pymysql python-dotenv \
        || die "pip3 install failed — ensure pip3 is installed (apt install python3-pip)"
    chown -R asterisk:asterisk "$AGI_PYLIBS"
    ok "AGI Python dependencies installed to $AGI_PYLIBS"

    # ── Asterisk systemd environment drop-in ───────────────────────────
    # Inject all env vars the AGI scripts need directly into the asterisk
    # service so child processes inherit them without any file I/O.
    DATABASE_URL=$(grep -E '^DATABASE_URL=' "$PROJECT_DIR/.env" | cut -d= -f2-)
    [ -z "$DATABASE_URL" ] && die "DATABASE_URL not found in .env"

    mkdir -p /etc/systemd/system/asterisk.service.d
    cat > /etc/systemd/system/asterisk.service.d/hash-env.conf << EOF
[Service]
Type=simple
PIDFile=
Environment="STT_TTS_PROJECT_DIR=$PROJECT_DIR"
Environment="PYTHONPATH=$AGI_PYLIBS"
Environment="DATABASE_URL=$DATABASE_URL"
EOF
    systemctl daemon-reload
    ok "Asterisk systemd drop-in written with STT_TTS_PROJECT_DIR, PYTHONPATH, DATABASE_URL"

    # ── Set astagidir in asterisk.conf ─────────────────────────────────
    ASTERISK_CONF="/etc/asterisk/asterisk.conf"
    if [ -f "$ASTERISK_CONF" ]; then
        if grep -q "^\[directories\]" "$ASTERISK_CONF"; then
            if ! grep -q "astagidir" "$ASTERISK_CONF"; then
                sed -i '/^\[directories\]/a astagidir => /var/lib/asterisk/agi-bin' "$ASTERISK_CONF"
            fi
        else
            printf '\n[directories]\nastagidir => /var/lib/asterisk/agi-bin\n' >> "$ASTERISK_CONF"
        fi
        ok "astagidir => /var/lib/asterisk/agi-bin set in asterisk.conf"
    else
        warn "asterisk.conf not found — astagidir not set (Asterisk may use wrong AGI path)"
    fi

    # ── Verify AGI imports work as the asterisk user ───────────────────
    echo "[*] Verifying AGI script imports as asterisk user..."
    if id asterisk &>/dev/null; then
        VERIFY_OUT=$(sudo -u asterisk \
            STT_TTS_PROJECT_DIR="$PROJECT_DIR" \
            PYTHONPATH="$AGI_PYLIBS" \
            DATABASE_URL="$DATABASE_URL" \
            python3 - << PYVERIFY 2>&1
import sys
sys.path.insert(0, "$AGI_BIN")
from agi_lib import agi_io, audio, db, pipeline
print("imports OK")
PYVERIFY
        )
        if echo "$VERIFY_OUT" | grep -q "imports OK"; then
            ok "AGI imports verified (asterisk user can load all dependencies)"
        else
            warn "AGI import check failed:"
            echo "$VERIFY_OUT"
            warn "Calls will fail until the above is resolved"
        fi
    fi

    # ── Asterisk config files ──────────────────────────────────────
    # The repo is the single source of truth. Back up then replace both files.
    AST_CONF="/etc/asterisk"
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)

    # pjsip
    if [ -f "$AST_CONF/pjsip.conf" ]; then
        cp "$AST_CONF/pjsip.conf" "$AST_CONF/pjsip.conf.bak.$TIMESTAMP"
        ok "Backed up existing pjsip.conf → pjsip.conf.bak.$TIMESTAMP"
    fi
    if [ -n "$SERVER_PUBLIC_IP" ] && ! echo "$SERVER_PUBLIC_IP" | grep -qi "YOUR_SERVER"; then
        sed "s/YOUR_SERVER_PUBLIC_IP/$SERVER_PUBLIC_IP/g" "$AGI_SRC/pjsip.conf" > "$AST_CONF/pjsip.conf"
        ok "pjsip.conf installed with external IP $SERVER_PUBLIC_IP"
    else
        cp "$AGI_SRC/pjsip.conf" "$AST_CONF/pjsip.conf"
        warn "pjsip.conf installed with placeholder IP — set SERVER_PUBLIC_IP in .env and re-run"
    fi

    # extensions (dialplan)
    if [ -f "$AST_CONF/extensions.conf" ]; then
        cp "$AST_CONF/extensions.conf" "$AST_CONF/extensions.conf.bak.$TIMESTAMP"
        ok "Backed up existing extensions.conf → extensions.conf.bak.$TIMESTAMP"
    fi
    cp "$AGI_SRC/extensions.conf" "$AST_CONF/extensions.conf"
    ok "extensions.conf replaced from repo"

    # ── HASH IVR audio prompts ─────────────────────────────────────
    AST_SOUNDS="/var/lib/asterisk/sounds"
    MEDIA_SRC="$PROJECT_DIR/media"

    if [ -d "$MEDIA_SRC" ] && [ -n "$(ls -A "$MEDIA_SRC"/*.wav 2>/dev/null)" ]; then
        echo "[*] Installing HASH IVR audio prompts to $AST_SOUNDS ..."
        # Copy to root and language subdir (Asterisk looks in en/ first)
        mkdir -p "$AST_SOUNDS/en"
        for wav in "$MEDIA_SRC"/*.wav; do
            cp "$wav" "$AST_SOUNDS/"
            cp "$wav" "$AST_SOUNDS/en/"
        done
        if id asterisk &>/dev/null; then
            chown asterisk:asterisk "$AST_SOUNDS"/hash-*.wav "$AST_SOUNDS/en"/hash-*.wav
        fi
        chmod 644 "$AST_SOUNDS"/hash-*.wav "$AST_SOUNDS/en"/hash-*.wav
        ok "HASH audio prompts installed to $AST_SOUNDS"
    else
        warn "No audio files found in $MEDIA_SRC/"
        echo "   Generate them first (needs AUTH_TOKEN in .env):"
        echo "   source .venv/bin/activate && python scripts/generate_media.py"
        echo "   Then re-run: sudo bash install.sh"
    fi

    # Disable chan_sip so it doesn't compete with res_pjsip on port 5060
    MODULES_CONF="/etc/asterisk/modules.conf"
    if [ -f "$MODULES_CONF" ]; then
        if ! grep -q "noload => chan_sip.so" "$MODULES_CONF"; then
            echo "noload => chan_sip.so" >> "$MODULES_CONF"
            ok "chan_sip.so disabled in modules.conf (res_pjsip will own port 5060)"
        else
            ok "chan_sip.so already disabled in modules.conf"
        fi
    else
        warn "modules.conf not found at $MODULES_CONF — skipping chan_sip disable"
    fi

    # Restart Asterisk via systemd so it picks up the updated environment
    # drop-in (PYTHONPATH, STT_TTS_PROJECT_DIR). Using "core restart now" only
    # re-execs the process and inherits the old environment.
    if systemctl is-active --quiet asterisk 2>/dev/null; then
        asterisk -rx "dialplan reload" && ok "Asterisk dialplan reloaded"
        systemctl restart asterisk     && ok "Asterisk restarted (applied modules.conf changes)"
    elif asterisk -rx "core show version" &>/dev/null; then
        asterisk -rx "dialplan reload" && ok "Asterisk dialplan reloaded"
        asterisk -rx "core restart now"
        warn "Asterisk is not managed by systemd — environment variables may not be set for AGI scripts"
        warn "Run: systemctl enable asterisk && systemctl restart asterisk"
    else
        warn "Asterisk is not running — start it with: systemctl start asterisk"
    fi
fi

# ── 7. Systemd service ─────────────────────────────────────────────
echo ""
echo "=== Step 6: Systemd Service ==="

SERVICE_DEST="/etc/systemd/system/$SERVICE_NAME.service"

cat > "$SERVICE_DEST" << EOF
[Unit]
Description=STT-TTS Pipeline API Service
After=network.target

[Service]
Type=simple
User=$PROJECT_USER
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/.venv/bin"
EnvironmentFile=-$PROJECT_DIR/.env
ExecStart=$PROJECT_DIR/.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$SERVICE_NAME

[Install]
WantedBy=multi-user.target
EOF

chmod 644 "$SERVICE_DEST"

# Set project ownership
chown -R "$PROJECT_USER:$PROJECT_USER" "$PROJECT_DIR"

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"

ok "Systemd service installed and started"

# ── Done ───────────────────────────────────────────────────────────
echo ""
echo "============================================"
ok "Installation complete!"
echo "============================================"
echo ""
echo "Service commands:"
echo "  Status:   sudo systemctl status $SERVICE_NAME"
echo "  Logs:     sudo journalctl -u $SERVICE_NAME -f"
echo "  Restart:  sudo systemctl restart $SERVICE_NAME"
echo ""
echo "Verify:"
echo "  curl http://localhost:8000/api/v1/health"
echo ""

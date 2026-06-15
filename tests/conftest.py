"""
Shared fixtures for all tests.

Env vars are set here BEFORE any app imports so that:
  - app/core/config.py picks up the test token (no RuntimeError)
  - app/core/database.py uses the SQLite test DB (not the real MySQL DB)
  - dashboard auth uses predictable credentials
"""

import os
import sys

# AGI scripts use bare `from agi_lib import ...` (sibling-relative) because
# Asterisk runs them with asterisk/ as the working directory. Add asterisk/
# to sys.path so test imports like `from asterisk.ai_assistant import ...`
# can resolve agi_lib when running from the project root.
_ASTERISK_DIR = os.path.join(os.path.dirname(__file__), "..", "asterisk")
if _ASTERISK_DIR not in sys.path:
    sys.path.insert(0, os.path.abspath(_ASTERISK_DIR))

os.environ.setdefault("HASH_PBX_ALLOW_INSECURE_DEFAULTS", "1")
os.environ.setdefault("HASH_PBX_NO_HEARTBEAT", "1")
os.environ.setdefault("AUTH_TOKEN", "test-sunbird-token")
os.environ.setdefault("API_TOKEN", "test-api-token")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_hash_pbx.db")
os.environ.setdefault("DASHBOARD_USERNAME", "testuser")
os.environ.setdefault("DASHBOARD_PASSWORD", "testpass")
os.environ.setdefault("DASHBOARD_SECRET_KEY", "test-secret-key-do-not-use-in-prod")
os.environ.setdefault("HASHIE_CHAT_URL", "http://localhost:9999/fake-agent")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, engine
from app.main import app
from app.models import AsteriskCDR, Call, CallMetrics, SystemLog  # noqa: F401


@pytest.fixture(scope="session", autouse=True)
def create_tables():
    """Create all tables once for the whole test session, drop after."""
    import app.models  # noqa: F401 — ensures models register with Base
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """TestClient pre-loaded with the bearer token required by /api/v1/ endpoints."""
    token = os.environ.get("API_TOKEN", "test-api-token")
    with TestClient(
        app,
        raise_server_exceptions=True,
        headers={"Authorization": f"Bearer {token}"},
    ) as c:
        yield c


@pytest.fixture
def client_no_auth():
    """TestClient with no Authorization header — for testing 401 responses."""
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture
def auth_client(client):
    """TestClient with a logged-in session."""
    resp = client.post(
        "/login",
        data={"username": "testuser", "password": "testpass"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    return client


@pytest.fixture
def db_session():
    """Yield a SQLAlchemy session for direct DB manipulation in tests."""
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def sample_call(db_session):
    """Insert one completed call row and return it."""
    call = Call(
        call_id="HASH-20260611-120000-0",
        caller_id="256700000001",
        extension="8446",
        language="English",
        speaker_id=248,
        status="completed",
        q1_input_text="What causes malaria?",
        q1_output_text="Malaria is caused by the Plasmodium parasite.",
        q1_detected_language="English",
        q1_input_audio="input-HASH-20260611-120000-0-1.wav",
        q2_input_text="How is it treated?",
        q2_output_text="Malaria is treated with antimalarial medications.",
        q2_detected_language="English",
        q2_input_audio="input-HASH-20260611-120000-0-2.wav",
    )
    db_session.add(call)
    db_session.commit()
    db_session.refresh(call)
    yield call
    db_session.delete(call)
    db_session.commit()


@pytest.fixture
def sample_metrics(db_session, sample_call):
    """Insert call_metrics rows for the sample call."""
    m1 = CallMetrics(
        call_id=sample_call.call_id,
        question_number=1,
        stt_duration=1.2,
        agent_duration=3.4,
        tts_duration=0.9,
        total_duration=5.5,
        audio_url="https://example.com/audio1.wav",
    )
    m2 = CallMetrics(
        call_id=sample_call.call_id,
        question_number=2,
        stt_duration=1.1,
        agent_duration=2.8,
        tts_duration=0.8,
        total_duration=4.7,
        audio_url="https://example.com/audio2.wav",
    )
    db_session.add_all([m1, m2])
    db_session.commit()
    yield m1, m2
    db_session.delete(m1)
    db_session.delete(m2)
    db_session.commit()

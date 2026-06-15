"""Tests for all REST API endpoints under /api/v1/."""

import pytest


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

class TestAPIAuth:
    """Bearer token enforcement — /health is exempt, everything else requires it."""

    def test_health_accessible_without_token(self, client_no_auth):
        resp = client_no_auth.get("/api/v1/health")
        assert resp.status_code == 200

    def test_speakers_without_token_returns_401(self, client_no_auth):
        resp = client_no_auth.get("/api/v1/speakers")
        assert resp.status_code == 401

    def test_history_without_token_returns_401(self, client_no_auth):
        resp = client_no_auth.get("/api/v1/history")
        assert resp.status_code == 401

    def test_logs_without_token_returns_401(self, client_no_auth):
        resp = client_no_auth.get("/api/v1/logs")
        assert resp.status_code == 401

    def test_wrong_token_returns_401(self, client_no_auth):
        resp = client_no_auth.get(
            "/api/v1/speakers",
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert resp.status_code == 401

    def test_correct_token_allows_access(self, client):
        resp = client.get("/api/v1/speakers")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class TestHealth:
    def test_health_returns_200(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200

    def test_health_contains_service_name(self, client):
        resp = client.get("/api/v1/health")
        data = resp.json()
        assert "service" in data
        assert "HASH PBX" in data["service"]

    def test_health_contains_endpoints_status(self, client):
        resp = client.get("/api/v1/health")
        data = resp.json()
        assert "endpoints" in data
        assert "stt" in data["endpoints"]
        assert "tts" in data["endpoints"]
        assert "language_id" in data["endpoints"]


# ---------------------------------------------------------------------------
# Speakers
# ---------------------------------------------------------------------------

class TestSpeakers:
    def test_speakers_returns_200(self, client):
        resp = client.get("/api/v1/speakers")
        assert resp.status_code == 200

    def test_speakers_contains_known_languages(self, client):
        resp = client.get("/api/v1/speakers")
        speakers = resp.json()["speakers"]
        for code in ("eng", "lug", "ach", "teo", "nyn", "lgg", "swa"):
            assert code in speakers

    def test_speakers_values_are_integers(self, client):
        resp = client.get("/api/v1/speakers")
        for code, speaker_id in resp.json()["speakers"].items():
            assert isinstance(speaker_id, int), f"{code} speaker_id is not int"


# ---------------------------------------------------------------------------
# History — calls
# ---------------------------------------------------------------------------

class TestHistoryCreate:
    PAYLOAD = {
        "call_id": "API-TEST-CREATE-001",
        "caller_id": "256700000099",
        "extension": "8446",
        "language": "eng",
        "speaker_id": 248,
        "status": "in_progress",
    }

    def teardown_method(self):
        from app.core.database import SessionLocal
        from app.models import Call
        db = SessionLocal()
        db.query(Call).filter(Call.call_id == self.PAYLOAD["call_id"]).delete()
        db.commit()
        db.close()

    def test_create_call_returns_201(self, client):
        resp = client.post("/api/v1/history", json=self.PAYLOAD)
        assert resp.status_code == 201

    def test_create_call_returns_data(self, client):
        resp = client.post("/api/v1/history", json=self.PAYLOAD)
        data = resp.json()
        assert data["call_id"] == self.PAYLOAD["call_id"]
        assert data["caller_id"] == self.PAYLOAD["caller_id"]
        assert "id" in data

    def test_create_call_missing_required_field_returns_422(self, client):
        resp = client.post("/api/v1/history", json={"caller_id": "256700000099"})
        assert resp.status_code == 422


class TestHistoryList:
    def test_list_returns_200(self, client):
        resp = client.get("/api/v1/history")
        assert resp.status_code == 200

    def test_list_returns_array(self, client):
        resp = client.get("/api/v1/history")
        assert isinstance(resp.json(), list)

    def test_list_contains_sample_call(self, client, sample_call):
        resp = client.get("/api/v1/history")
        call_ids = [c["call_id"] for c in resp.json()]
        assert sample_call.call_id in call_ids

    def test_list_limit_param(self, client, sample_call):
        resp = client.get("/api/v1/history?limit=1")
        assert resp.status_code == 200
        assert len(resp.json()) <= 1

    def test_list_offset_param(self, client):
        resp = client.get("/api/v1/history?offset=99999")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_invalid_limit_returns_422(self, client):
        resp = client.get("/api/v1/history?limit=0")
        assert resp.status_code == 422


class TestHistoryStats:
    def test_stats_returns_200(self, client):
        resp = client.get("/api/v1/history/stats")
        assert resp.status_code == 200

    def test_stats_contains_expected_keys(self, client, sample_call):
        resp = client.get("/api/v1/history/stats")
        data = resp.json()
        assert "total_calls" in data
        assert "languages" in data
        assert "statuses" in data
        assert "avg_durations" in data

    def test_stats_total_increments_with_data(self, client, sample_call):
        resp = client.get("/api/v1/history/stats")
        assert resp.json()["total_calls"] >= 1


class TestHistoryDetail:
    def test_existing_call_returns_200(self, client, sample_call):
        resp = client.get(f"/api/v1/history/{sample_call.call_id}")
        assert resp.status_code == 200

    def test_existing_call_returns_correct_data(self, client, sample_call):
        resp = client.get(f"/api/v1/history/{sample_call.call_id}")
        data = resp.json()
        assert data["call_id"] == sample_call.call_id
        assert data["caller_id"] == sample_call.caller_id

    def test_nonexistent_call_returns_404(self, client):
        resp = client.get("/api/v1/history/DOES-NOT-EXIST-0")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

class TestMetrics:
    CALL_ID = "API-TEST-METRICS-001"

    def setup_method(self):
        from app.core.database import SessionLocal
        from app.models import Call
        db = SessionLocal()
        if not db.query(Call).filter(Call.call_id == self.CALL_ID).first():
            db.add(Call(call_id=self.CALL_ID, q1_input_text="q", q1_output_text="a", q1_detected_language="eng"))
            db.commit()
        db.close()

    def teardown_method(self):
        from app.core.database import SessionLocal
        from app.models import Call, CallMetrics
        db = SessionLocal()
        db.query(CallMetrics).filter(CallMetrics.call_id == self.CALL_ID).delete()
        db.query(Call).filter(Call.call_id == self.CALL_ID).delete()
        db.commit()
        db.close()

    def test_create_metrics_returns_201(self, client):
        resp = client.post("/api/v1/metrics", json={
            "call_id": self.CALL_ID,
            "question_number": 1,
            "stt_duration": 1.2,
            "agent_duration": 2.3,
            "tts_duration": 0.9,
            "total_duration": 4.4,
        })
        assert resp.status_code == 201

    def test_create_metrics_returns_data(self, client):
        resp = client.post("/api/v1/metrics", json={
            "call_id": self.CALL_ID,
            "question_number": 1,
            "total_duration": 3.5,
        })
        data = resp.json()
        assert data["call_id"] == self.CALL_ID
        assert data["question_number"] == 1
        assert "id" in data

    def test_get_metrics_for_call_returns_200(self, client, sample_metrics):
        resp = client.get(f"/api/v1/metrics/{sample_metrics[0].call_id}")
        assert resp.status_code == 200

    def test_get_metrics_returns_list(self, client, sample_metrics):
        resp = client.get(f"/api/v1/metrics/{sample_metrics[0].call_id}")
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_get_metrics_ordered_by_question_number(self, client, sample_metrics):
        resp = client.get(f"/api/v1/metrics/{sample_metrics[0].call_id}")
        q_nums = [m["question_number"] for m in resp.json()]
        assert q_nums == sorted(q_nums)

    def test_get_metrics_nonexistent_call_returns_404(self, client):
        resp = client.get("/api/v1/metrics/DOES-NOT-EXIST-0")
        assert resp.status_code == 404

    def test_create_metrics_missing_required_fields_returns_422(self, client):
        resp = client.post("/api/v1/metrics", json={"question_number": 1})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Caller Preferences
# ---------------------------------------------------------------------------

class TestPreferences:
    CALLER_ID = "api-test-caller-prefs"

    def teardown_method(self):
        from app.core.database import SessionLocal
        from app.models.caller_preferences import CallerPreferences
        db = SessionLocal()
        db.query(CallerPreferences).filter(CallerPreferences.caller_id == self.CALLER_ID).delete()
        db.commit()
        db.close()

    def test_list_preferences_returns_200(self, client):
        resp = client.get("/api/v1/preferences")
        assert resp.status_code == 200

    def test_list_preferences_returns_array(self, client):
        resp = client.get("/api/v1/preferences")
        assert isinstance(resp.json(), list)

    def test_set_preference_creates_record(self, client):
        resp = client.put(f"/api/v1/preferences/{self.CALLER_ID}", json={"language": "lug"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["caller_id"] == self.CALLER_ID
        assert data["language"] == "lug"

    def test_set_preference_updates_existing(self, client):
        client.put(f"/api/v1/preferences/{self.CALLER_ID}", json={"language": "lug"})
        resp = client.put(f"/api/v1/preferences/{self.CALLER_ID}", json={"language": "eng"})
        assert resp.status_code == 200
        assert resp.json()["language"] == "eng"

    def test_get_preference_existing_caller(self, client):
        client.put(f"/api/v1/preferences/{self.CALLER_ID}", json={"language": "ach"})
        resp = client.get(f"/api/v1/preferences/{self.CALLER_ID}")
        assert resp.status_code == 200
        assert resp.json()["language"] == "ach"

    def test_get_preference_nonexistent_caller_returns_404(self, client):
        resp = client.get("/api/v1/preferences/caller-that-does-not-exist")
        assert resp.status_code == 404

    def test_set_preference_missing_language_returns_422(self, client):
        resp = client.put(f"/api/v1/preferences/{self.CALLER_ID}", json={})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# CDR
# ---------------------------------------------------------------------------

class TestCDR:
    UNIQUEID = "api-test-cdr-1234.99"

    def teardown_method(self):
        from app.core.database import SessionLocal
        from app.models.cdr import AsteriskCDR
        db = SessionLocal()
        db.query(AsteriskCDR).filter(AsteriskCDR.uniqueid == self.UNIQUEID).delete()
        db.commit()
        db.close()

    def test_insert_cdr_returns_201(self, client):
        resp = client.post("/api/v1/cdr", json={
            "uniqueid": self.UNIQUEID,
            "call_id": "test-call",
            "src": "256700000001",
            "dst": "8446",
            "duration": 90,
            "billsec": 85,
            "disposition": "ANSWERED",
        })
        assert resp.status_code == 201

    def test_insert_cdr_returns_data(self, client):
        resp = client.post("/api/v1/cdr", json={"uniqueid": self.UNIQUEID, "src": "256700000001"})
        data = resp.json()
        assert data["uniqueid"] == self.UNIQUEID
        assert "id" in data

    def test_insert_cdr_missing_uniqueid_returns_422(self, client):
        resp = client.post("/api/v1/cdr", json={"src": "256700000001"})
        assert resp.status_code == 422

    def test_list_cdr_returns_200(self, client):
        resp = client.get("/api/v1/cdr")
        assert resp.status_code == 200

    def test_list_cdr_returns_array(self, client):
        resp = client.get("/api/v1/cdr")
        assert isinstance(resp.json(), list)

    def test_get_cdr_existing_returns_200(self, client):
        client.post("/api/v1/cdr", json={"uniqueid": self.UNIQUEID})
        resp = client.get(f"/api/v1/cdr/{self.UNIQUEID}")
        assert resp.status_code == 200
        assert resp.json()["uniqueid"] == self.UNIQUEID

    def test_get_cdr_nonexistent_returns_404(self, client):
        resp = client.get("/api/v1/cdr/does-not-exist.0")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# System Logs
# ---------------------------------------------------------------------------

class TestLogs:
    LOG_PAYLOAD = {
        "level": "INFO",
        "component": "api",
        "event_type": "test_event",
        "message": "Test log entry from test_api.py",
        "call_id": None,
        "details": None,
    }

    def test_write_log_returns_201(self, client):
        resp = client.post("/api/v1/logs", json=self.LOG_PAYLOAD)
        assert resp.status_code == 201

    def test_write_log_returns_data(self, client):
        resp = client.post("/api/v1/logs", json=self.LOG_PAYLOAD)
        data = resp.json()
        assert data["level"] == "INFO"
        assert data["component"] == "api"
        assert data["event_type"] == "test_event"
        assert "id" in data

    def test_write_log_missing_required_fields_returns_422(self, client):
        resp = client.post("/api/v1/logs", json={"level": "INFO"})
        assert resp.status_code == 422

    def test_list_logs_returns_200(self, client):
        resp = client.get("/api/v1/logs")
        assert resp.status_code == 200

    def test_list_logs_returns_array(self, client):
        resp = client.get("/api/v1/logs")
        assert isinstance(resp.json(), list)

    def test_list_logs_filter_by_level(self, client):
        client.post("/api/v1/logs", json={**self.LOG_PAYLOAD, "level": "ERROR", "event_type": "err_test"})
        resp = client.get("/api/v1/logs?level=ERROR")
        assert resp.status_code == 200
        for entry in resp.json():
            assert entry["level"] == "ERROR"

    def test_list_logs_level_filter_case_insensitive(self, client):
        resp = client.get("/api/v1/logs?level=info")
        assert resp.status_code == 200

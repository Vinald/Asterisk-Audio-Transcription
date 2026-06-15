"""Tests for dashboard page routes — rendering, pagination, filters, edge cases."""

import pytest


class TestOverview:
    def test_overview_renders(self, auth_client):
        resp = auth_client.get("/dashboard")
        assert resp.status_code == 200
        assert "Overview" in resp.text

    def test_overview_shows_call_data(self, auth_client, sample_call):
        resp = auth_client.get("/dashboard")
        assert resp.status_code == 200
        # Caller ID should appear in the recent calls table
        assert sample_call.caller_id in resp.text


class TestCallsList:
    def test_calls_list_renders(self, auth_client, sample_call):
        resp = auth_client.get("/dashboard/calls")
        assert resp.status_code == 200
        assert sample_call.call_id in resp.text

    def test_filter_by_status(self, auth_client, sample_call):
        resp = auth_client.get("/dashboard/calls?status=completed")
        assert resp.status_code == 200
        assert sample_call.call_id in resp.text

    def test_filter_by_status_no_match(self, auth_client, sample_call):
        resp = auth_client.get("/dashboard/calls?status=error_q1")
        assert resp.status_code == 200
        assert sample_call.call_id not in resp.text

    def test_filter_by_language(self, auth_client, sample_call):
        resp = auth_client.get("/dashboard/calls?language=English")
        assert resp.status_code == 200
        assert sample_call.call_id in resp.text

    def test_filter_by_valid_date_range(self, auth_client, sample_call):
        resp = auth_client.get("/dashboard/calls?date_from=2026-01-01&date_to=2026-12-31")
        assert resp.status_code == 200

    def test_invalid_date_does_not_500(self, auth_client):
        """Bug fix: invalid date_from/to should not crash the route."""
        resp = auth_client.get("/dashboard/calls?date_from=not-a-date&date_to=also-bad")
        assert resp.status_code == 200

    def test_page_zero_treated_as_page_one(self, auth_client, sample_call):
        """Bug fix: page=0 should not produce a negative SQL offset."""
        resp = auth_client.get("/dashboard/calls?page=0")
        assert resp.status_code == 200
        assert sample_call.call_id in resp.text

    def test_negative_page_treated_as_page_one(self, auth_client, sample_call):
        resp = auth_client.get("/dashboard/calls?page=-5")
        assert resp.status_code == 200

    def test_page_beyond_total_returns_empty_not_error(self, auth_client):
        resp = auth_client.get("/dashboard/calls?page=99999")
        assert resp.status_code == 200


class TestCallDetail:
    def test_existing_call_renders(self, auth_client, sample_call, sample_metrics):
        resp = auth_client.get(f"/dashboard/calls/{sample_call.call_id}")
        assert resp.status_code == 200
        assert sample_call.q1_input_text in resp.text
        assert sample_call.q1_output_text in resp.text

    def test_existing_call_shows_metrics(self, auth_client, sample_call, sample_metrics):
        resp = auth_client.get(f"/dashboard/calls/{sample_call.call_id}")
        assert resp.status_code == 200
        # Timing values should appear
        assert "1.2" in resp.text  # stt_duration Q1
        assert "5.5" in resp.text  # total_duration Q1

    def test_nonexistent_call_returns_404(self, auth_client):
        resp = auth_client.get("/dashboard/calls/HASH-00000000-000000-0")
        assert resp.status_code == 404
        assert "404" in resp.text


class TestMetricsList:
    def test_metrics_list_renders(self, auth_client, sample_metrics):
        resp = auth_client.get("/dashboard/metrics")
        assert resp.status_code == 200

    def test_metrics_shows_durations(self, auth_client, sample_metrics):
        resp = auth_client.get("/dashboard/metrics")
        assert resp.status_code == 200
        assert "1.20 s" in resp.text  # Q1 stt_duration

    def test_metrics_page_zero_safe(self, auth_client):
        resp = auth_client.get("/dashboard/metrics?page=0")
        assert resp.status_code == 200


class TestLogsList:
    def test_logs_list_renders(self, auth_client):
        resp = auth_client.get("/dashboard/logs")
        assert resp.status_code == 200
        assert "System Logs" in resp.text

    def test_filter_by_level(self, auth_client):
        resp = auth_client.get("/dashboard/logs?level=ERROR")
        assert resp.status_code == 200

    def test_logs_page_zero_safe(self, auth_client):
        resp = auth_client.get("/dashboard/logs?page=0")
        assert resp.status_code == 200

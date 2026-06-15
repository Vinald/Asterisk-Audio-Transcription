"""Tests for CSV export endpoints."""

import csv
import io


class TestCallsCSV:
    def test_export_requires_auth(self, client):
        resp = client.get("/export/calls.csv", follow_redirects=False)
        assert resp.status_code == 303
        assert "/login" in resp.headers["location"]

    def test_export_returns_csv(self, auth_client, sample_call):
        resp = auth_client.get("/export/calls.csv")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/csv")
        assert 'attachment; filename=calls.csv' in resp.headers["content-disposition"]

    def test_export_has_header_row(self, auth_client):
        resp = auth_client.get("/export/calls.csv")
        reader = csv.reader(io.StringIO(resp.text))
        header = next(reader)
        assert "call_id" in header
        assert "caller_id" in header
        assert "language" in header
        assert "status" in header

    def test_export_contains_call_data(self, auth_client, sample_call):
        resp = auth_client.get("/export/calls.csv")
        assert sample_call.call_id in resp.text
        assert sample_call.caller_id in resp.text

    def test_export_no_none_strings(self, auth_client, sample_call):
        """Bug fix: null DB fields must export as empty strings, not 'None'."""
        resp = auth_client.get("/export/calls.csv")
        rows = list(csv.reader(io.StringIO(resp.text)))
        for row in rows[1:]:  # skip header
            for cell in row:
                assert cell != "None", f"Found literal 'None' in CSV: {row}"


class TestCDRCSV:
    def test_export_requires_auth(self, client):
        resp = client.get("/export/cdr.csv", follow_redirects=False)
        assert resp.status_code == 303

    def test_export_returns_csv(self, auth_client):
        resp = auth_client.get("/export/cdr.csv")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/csv")

    def test_export_has_header_row(self, auth_client):
        resp = auth_client.get("/export/cdr.csv")
        reader = csv.reader(io.StringIO(resp.text))
        header = next(reader)
        assert "uniqueid" in header
        assert "call_id" in header
        assert "duration" in header


class TestMetricsCSV:
    def test_export_requires_auth(self, client):
        resp = client.get("/export/metrics.csv", follow_redirects=False)
        assert resp.status_code == 303

    def test_export_returns_csv(self, auth_client, sample_metrics):
        resp = auth_client.get("/export/metrics.csv")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/csv")

    def test_export_has_header_row(self, auth_client):
        resp = auth_client.get("/export/metrics.csv")
        reader = csv.reader(io.StringIO(resp.text))
        header = next(reader)
        assert "call_id" in header
        assert "question_number" in header
        assert "total_duration" in header

    def test_export_contains_metric_data(self, auth_client, sample_call, sample_metrics):
        resp = auth_client.get("/export/metrics.csv")
        assert sample_call.call_id in resp.text

    def test_export_no_none_strings(self, auth_client, sample_metrics):
        """Bug fix: null fields must not appear as the string 'None'."""
        resp = auth_client.get("/export/metrics.csv")
        rows = list(csv.reader(io.StringIO(resp.text)))
        for row in rows[1:]:
            for cell in row:
                assert cell != "None", f"Found literal 'None' in CSV: {row}"

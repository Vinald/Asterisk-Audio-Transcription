"""Tests for dashboard authentication — login, logout, and access control."""

import pytest


class TestLoginPage:
    def test_login_page_renders(self, client):
        resp = client.get("/login")
        assert resp.status_code == 200
        assert "Sign in" in resp.text

    def test_authenticated_user_redirected_away_from_login(self, auth_client):
        resp = auth_client.get("/login", follow_redirects=False)
        assert resp.status_code == 303
        assert resp.headers["location"] == "/dashboard"


class TestLoginSubmit:
    def test_valid_credentials_redirect_to_dashboard(self, client):
        resp = client.post(
            "/login",
            data={"username": "testuser", "password": "testpass"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert resp.headers["location"] == "/dashboard"

    def test_wrong_password_shows_error(self, client):
        resp = client.post(
            "/login",
            data={"username": "testuser", "password": "wrongpassword"},
        )
        assert resp.status_code == 200
        assert "Invalid username or password" in resp.text

    def test_wrong_username_shows_error(self, client):
        resp = client.post(
            "/login",
            data={"username": "nobody", "password": "testpass"},
        )
        assert resp.status_code == 200
        assert "Invalid username or password" in resp.text

    def test_empty_credentials_show_error(self, client):
        resp = client.post(
            "/login",
            data={"username": "", "password": ""},
        )
        assert resp.status_code == 200
        assert "Invalid username or password" in resp.text


class TestLogout:
    def test_logout_redirects_to_login(self, auth_client):
        resp = auth_client.get("/logout", follow_redirects=False)
        assert resp.status_code == 303
        assert resp.headers["location"] == "/login"

    def test_after_logout_dashboard_requires_login(self, auth_client):
        auth_client.get("/logout", follow_redirects=True)
        resp = auth_client.get("/dashboard", follow_redirects=False)
        assert resp.status_code == 303
        assert "/login" in resp.headers["location"]


class TestAccessControl:
    """Every dashboard route must redirect unauthenticated requests to /login."""

    protected_routes = [
        "/dashboard",
        "/dashboard/calls",
        "/dashboard/logs",
        "/dashboard/metrics",
        "/export/calls.csv",
        "/export/cdr.csv",
        "/export/metrics.csv",
    ]

    @pytest.mark.parametrize("route", protected_routes)
    def test_unauthenticated_access_redirects(self, client, route):
        resp = client.get(route, follow_redirects=False)
        assert resp.status_code == 303
        assert "/login" in resp.headers["location"]

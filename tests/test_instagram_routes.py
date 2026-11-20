"""OAuth routes: state (CSRF) check, cookie flags, redirects. Network and MySQL are faked."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app import main
from app.dependencies import get_db
from app.integrations import instagram_graph
from app.models import IgAccount
from app.routers import instagram_api
from core.config import settings
from tests.conftest import Transport


@pytest.fixture
def web(db, graph, monkeypatch):
    monkeypatch.setattr(instagram_graph, "urllib_transport", Transport(graph))
    started = []
    monkeypatch.setattr(instagram_api, "sync_in_background", lambda account_id: started.append(account_id))
    main.app.dependency_overrides[get_db] = lambda: db
    client = TestClient(main.app, base_url="http://localhost:8000", follow_redirects=False)
    client.started = started
    yield client
    main.app.dependency_overrides.clear()


def _accounts(db) -> int:
    return db.scalar(select(func.count()).select_from(IgAccount))


def test_login_redirects_to_instagram_with_httponly_state_cookie(web):
    r = web.get("/auth/instagram/login")
    assert r.status_code == 303 and r.headers["location"].startswith("https://www.instagram.com/oauth/authorize")
    cookie = r.headers["set-cookie"]
    assert "ig_oauth_state=" in cookie and "HttpOnly" in cookie and "samesite=lax" in cookie.lower()
    state = r.cookies["ig_oauth_state"]
    assert f"state={state}" in r.headers["location"]


def test_callback_without_matching_state_is_rejected(web, db, graph):
    web.get("/auth/instagram/login")
    r = web.get("/auth/instagram/callback", params={"code": "C", "state": "forged"})
    assert r.headers["location"] == "/analytics?ig=state"
    assert graph.calls == [] and _accounts(db) == 0  # the code was never used


def test_callback_without_cookie_is_rejected(web, db):
    web.cookies.clear()
    r = web.get("/auth/instagram/callback", params={"code": "C", "state": "x"})
    assert r.headers["location"] == "/analytics?ig=state" and _accounts(db) == 0


def test_callback_user_denied(web, db):
    state = web.get("/auth/instagram/login").cookies["ig_oauth_state"]
    r = web.get("/auth/instagram/callback", params={"error": "access_denied", "state": state})
    assert r.headers["location"] == "/analytics?ig=denied" and _accounts(db) == 0


def test_callback_success_connects_and_starts_sync(web, db):
    state = web.get("/auth/instagram/login").cookies["ig_oauth_state"]
    r = web.get("/auth/instagram/callback", params={"code": "C#_", "state": state})
    assert r.headers["location"] == "/analytics?ig=connected"
    assert _accounts(db) == 1 and len(web.started) == 1
    s = web.get("/api/instagram/status").json()
    assert s["connected"] and s["username"] == "real.creator" and s["configured"]
    assert "token" not in str(s).lower().replace("token_expires_at", "")


def test_routes_disabled_when_not_configured(web, monkeypatch):
    monkeypatch.setattr(settings, "instagram_app_secret", "")
    assert web.get("/auth/instagram/login").status_code == 503


def test_sync_endpoint_needs_real_account(web):
    assert web.post("/api/instagram/sync").status_code == 404

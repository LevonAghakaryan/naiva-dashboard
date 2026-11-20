"""Test setup: in-memory SQLite (never the real MySQL) + a fake Instagram Graph API (no network)."""
from __future__ import annotations

import json
import sys
import urllib.parse
from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import models  # noqa: E402,F401  (registers all tables)
from core.config import settings  # noqa: E402
from core.database import Base  # noqa: E402

SHORT, LONG, REFRESHED = "SHORT-tok-123", "LONG-tok-456", "REFRESHED-tok-789"
IG_ID = "17841400000000001"


@pytest.fixture(autouse=True)
def _settings(monkeypatch):
    monkeypatch.setattr(settings, "encryption_key", Fernet.generate_key().decode())
    monkeypatch.setattr(settings, "instagram_app_id", "app-id-1")
    monkeypatch.setattr(settings, "instagram_app_secret", "APP-SECRET-xyz")
    monkeypatch.setattr(settings, "instagram_redirect_uri", "http://localhost:8000/auth/instagram/callback")
    monkeypatch.setattr(settings, "instagram_backfill_days", 5)
    monkeypatch.setattr(settings, "instagram_resync_days", 2)


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
    yield session
    session.close()
    engine.dispose()


class FakeGraph:
    """Answers like graph.instagram.com. Records every call; tweak behaviour via attributes."""

    def __init__(self):
        self.calls: list[tuple[str, str, dict]] = []
        self.account_type = "MEDIA_CREATOR"
        self.followers = 1000
        self.unsupported_metrics = {"reposts"}  # pretend this API version lacks it
        self.fail_with: tuple[int, dict] | None = None  # (status, payload) for every call
        self.fail_times = 0  # fail only the first N calls

    def __call__(self, method: str, url: str, form: dict | None, timeout: float):
        parsed = urllib.parse.urlparse(url)
        q = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
        self.calls.append((method, parsed.path, q | (form or {})))
        if self.fail_with and (self.fail_times == 0 or len(self.calls) <= self.fail_times):
            status, payload = self.fail_with
            return status, json.dumps(payload).encode()
        return 200, json.dumps(self.route(parsed, q, form)).encode()

    def _bad(self, msg="Invalid parameter"):
        raise _Respond(400, {"error": {"message": msg, "type": "OAuthException", "code": 100}})

    def route(self, parsed, q, form):
        host, path = parsed.netloc, parsed.path
        if host == "api.instagram.com":
            assert form["client_secret"] == "APP-SECRET-xyz"
            return {"data": [{"access_token": SHORT, "user_id": IG_ID, "permissions": "x"}]}
        if path == "/access_token":
            assert q["access_token"] == SHORT
            return {"access_token": LONG, "token_type": "bearer", "expires_in": 5184000}
        if path == "/refresh_access_token":
            return {"access_token": REFRESHED, "token_type": "bearer", "expires_in": 5184000}
        tail = path.split("/", 2)[2]  # strip /vXX.X/
        if tail == "me":
            return {"id": "app-scoped-1", "user_id": IG_ID, "username": "real.creator", "name": "Real Creator",
                    "account_type": self.account_type, "followers_count": self.followers,
                    "follows_count": 10, "media_count": 2}
        if tail == "me/media":
            return {"data": [
                {"id": "m1", "media_type": "VIDEO", "media_product_type": "REELS", "caption": "reel",
                 "permalink": "https://instagram.com/p/m1", "thumbnail_url": "https://cdn/t1.jpg",
                 "media_url": "https://cdn/v1.mp4", "timestamp": "2026-11-18T10:00:00+0000",
                 "like_count": 50, "comments_count": 5},
                {"id": "m2", "media_type": "IMAGE", "media_product_type": "FEED", "caption": "photo",
                 "permalink": "https://instagram.com/p/m2", "media_url": "https://cdn/i2.jpg",
                 "timestamp": "2026-11-15T10:00:00+0000", "like_count": 20, "comments_count": 2},
            ]}
        if tail == "me/stories":
            return {"data": []}
        if tail == "me/insights":
            return self._account_insights(q)
        if tail.endswith("/insights"):
            metrics = q["metric"].split(",")
            if self.unsupported_metrics & set(metrics):
                self._bad()
            return {"data": [{"name": m, "period": "lifetime", "values": [{"value": 7}]} for m in metrics]}
        raise AssertionError(f"unexpected call {path}")

    def _account_insights(self, q):
        metrics = q["metric"].split(",")
        if metrics == ["online_followers"]:
            return {"data": [{"name": "online_followers", "period": "lifetime", "values": [
                {"value": {str(h): 10 * h for h in range(24)}, "end_time": "2026-11-19T08:00:00+0000"},
                {"value": {}, "end_time": "2026-11-18T08:00:00+0000"},
            ]}]}
        if metrics == ["follower_demographics"]:
            if self.followers < 100:
                self._bad("Not enough followers")
            sample = {"age": {"25-34": 400, "18-24": 300}, "gender": {"F": 600, "M": 400},
                      "city": {"Yerevan, Yerevan": 500}, "country": {"AM": 700, "US": 100}}[q["breakdown"]]
            return {"data": [{"name": "follower_demographics", "total_value": {"breakdowns": [{
                "dimension_keys": [q["breakdown"]],
                "results": [{"dimension_values": [k], "value": v} for k, v in sample.items()]}]}}]}
        if self.unsupported_metrics & set(metrics):
            self._bad()
        if q.get("breakdown") == "follow_type":
            return {"data": [{"name": m, "total_value": {"value": 0, "breakdowns": [{
                "dimension_keys": ["follow_type"], "results": [
                    {"dimension_values": ["FOLLOWER"], "value": 3},
                    {"dimension_values": ["NON_FOLLOWER"], "value": 1}]}]}} for m in metrics]}
        return {"data": [{"name": m, "total_value": {"value": 100}} for m in metrics]}


class _Respond(Exception):
    def __init__(self, status, payload):
        self.status, self.payload = status, payload


class Transport:
    """Wraps FakeGraph so route() can raise _Respond for HTTP errors."""

    def __init__(self, graph: FakeGraph):
        self.graph = graph

    def __call__(self, method, url, form, timeout):
        try:
            return self.graph(method, url, form, timeout)
        except _Respond as r:
            return r.status, json.dumps(r.payload).encode()


@pytest.fixture
def graph():
    return FakeGraph()


@pytest.fixture
def client_factory(graph):
    from app.integrations.instagram_graph import InstagramClient

    transport = Transport(graph)
    return lambda token="": InstagramClient(token, transport=transport, sleep=lambda s: None)

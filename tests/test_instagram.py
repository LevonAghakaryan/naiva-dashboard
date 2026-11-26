"""Instagram connection + sync, end to end against a fake Graph API and SQLite."""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.integrations.instagram_graph import (
    InstagramAuthError,
    InstagramClient,
    InstagramError,
    InstagramRateLimit,
)
from app.models import (
    AccountDailyStats,
    AccountPeriodStats,
    AudienceOnlineHours,
    AudienceStats,
    IgAccount,
    Post,
    PostStats,
    User,
)
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.instagram_repository import InstagramRepository
from app.services.instagram_service import InstagramNoAccount, InstagramService, SyncBusy, _lock_for
from tests.conftest import IG_ID, TOKEN

NOW = datetime(2026, 11, 20, 10, 0)  # naive UTC → 14:00 in Yerevan, same date


def service(db, client_factory):
    return InstagramService(InstagramRepository(db), client_factory=client_factory, now=lambda: NOW)


def count(db, model) -> int:
    return db.scalar(select(func.count()).select_from(model))


# ------------------------------------------------------------------ OAuth / client

def test_authorize_url_has_state_config_and_redirect():
    url = InstagramClient.authorize_url("STATE123")
    assert url.startswith("https://www.facebook.com/v27.0/dialog/oauth?")
    assert "client_id=app-id-1" in url and "state=STATE123" in url
    assert "config_id=config-1" in url and "response_type=code" in url and "scope=" not in url
    assert "redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fauth%2Finstagram%2Fcallback" in url
    assert "APP-SECRET" not in url


def test_errors_never_leak_token_or_secret(graph, client_factory):
    graph.fail_with = (400, {"error": {"message": f"Bad token {TOKEN} / APP-SECRET-xyz", "type": "OAuthException",
                                       "code": 190}})
    with pytest.raises(InstagramAuthError) as exc:
        client_factory(TOKEN).profile()
    assert TOKEN not in str(exc.value) and "APP-SECRET-xyz" not in str(exc.value)


def test_rate_limit_is_not_auth_error(graph, client_factory):
    graph.fail_with = (400, {"error": {"message": "limit", "type": "OAuthException", "code": 4}})
    with pytest.raises(InstagramRateLimit):
        client_factory(TOKEN).profile()


def test_server_errors_are_retried(graph, client_factory):
    graph.fail_with, graph.fail_times = (500, {"error": {"message": "boom", "code": 2}}), 2
    assert client_factory(TOKEN).profile().username == "real.creator"
    assert len(graph.calls) == 3


def test_server_error_gives_up_after_retries(graph, client_factory):
    graph.fail_with = (503, {"error": {"message": "down", "code": 2}})
    with pytest.raises(InstagramError):
        client_factory(TOKEN).profile()
    assert len(graph.calls) == 3


def test_code_suffix_is_stripped(graph, client_factory):
    client_factory().exchange_code("abc#_")
    assert graph.calls[0][2]["code"] == "abc"


# ------------------------------------------------------------------ connect

def test_connect_creates_account_with_encrypted_token(db, client_factory):
    [acc] = service(db, client_factory).connect("CODE")
    assert acc.ig_user_id == IG_ID and acc.username == "real.creator" and acc.followers_count == 1000
    assert acc.access_token != TOKEN and acc.get_access_token() == TOKEN  # stored encrypted
    assert acc.token_expires_at is None  # never expires
    user = db.get(User, acc.user_id)
    assert user.email == f"ig-{IG_ID}@creatorly.local" and user.password_hash.startswith("!")


def test_reconnect_updates_same_account(db, client_factory):
    [a1] = service(db, client_factory).connect("CODE")
    [a2] = service(db, client_factory).connect("CODE2")
    assert a1.id == a2.id and count(db, IgAccount) == 1 and count(db, User) == 1


def test_connect_without_shared_account_is_rejected(db, graph, client_factory):
    graph.assigned = []
    with pytest.raises(InstagramNoAccount):
        service(db, client_factory).connect("CODE")
    assert count(db, IgAccount) == 0


def test_connect_with_ready_token(db, graph, client_factory):
    acc = service(db, client_factory).connect_token(TOKEN, IG_ID)
    assert acc.username == "real.creator" and acc.get_access_token() == TOKEN
    assert len(graph.calls) == 1  # no OAuth calls


# ------------------------------------------------------------------ sync

@pytest.fixture
def account(db, client_factory):
    return service(db, client_factory).connect("CODE")[0]


def test_first_sync_fills_all_tables(db, graph, client_factory, account):
    res = service(db, client_factory).sync(account)
    assert res.warnings == []
    assert res.days == 5  # instagram_backfill_days in tests

    days = {r.day: r for r in db.scalars(select(AccountDailyStats))}
    assert sorted(days) == [date(2026, 11, 16) + timedelta(days=i) for i in range(5)]
    today = days[date(2026, 11, 20)]
    assert today.reach == 100 and today.views == 100 and today.interactions == 100 and today.link_taps == 100
    assert today.new_follows == 3 and today.unfollows == 1 and today.non_follower_reach == 1
    assert today.reposts == 0  # unsupported metric skipped, not fatal
    # followers level: today from profile, each earlier day minus net (+2)
    assert [days[d].followers for d in sorted(days)] == [992, 994, 996, 998, 1000]

    periods = {(p.end_day, p.days) for p in db.scalars(select(AccountPeriodStats))}
    assert periods == {(date(2026, 11, 19), 7), (date(2026, 11, 12), 7),  # periods end yesterday
                       (date(2026, 11, 19), 30), (date(2026, 10, 20), 30)}

    posts = {p.ig_media_id: p for p in db.scalars(select(Post))}
    assert posts["m1"].type == "reels" and posts["m2"].type == "post"
    assert posts["m2"].thumbnail_url == "https://cdn/i2.jpg"  # image: media_url used as thumbnail
    assert posts["m1"].posted_at == datetime(2026, 11, 18, 10, 0)
    st = db.scalar(select(PostStats).where(PostStats.post_id == posts["m1"].id))
    assert st.likes == 50 and st.comments == 5 and st.views == 7 and st.saves == 7

    aud = {(a.breakdown, a.label): a.value for a in db.scalars(select(AudienceStats))}
    assert aud[("country", "AM")] == 700 and aud[("city", "Yerevan, Yerevan")] == 500
    # online_followers: 08:00 UTC Nov 18 + h → Yerevan (UTC+4) → Wed 12:00 for h=0
    hours = {(h.day, h.hour): h.value for h in db.scalars(select(AudienceOnlineHours))}
    assert len(hours) == 24 and hours[(2, 12)] == 0 and hours[(2, 13)] == 10
    assert account.last_synced_at is not None


def test_unsupported_metric_is_learned_once(db, graph, client_factory, account):
    service(db, client_factory).sync(account)
    rejected = [c for c in graph.calls if c[2].get("metric") == "reposts"]
    # account level: tried alone once; media: once per product type (REELS, FEED)
    assert len(rejected) == 3


def test_resync_is_idempotent(db, graph, client_factory, account):
    service(db, client_factory).sync(account)
    before = (count(db, AccountDailyStats), count(db, Post), count(db, PostStats), count(db, AudienceStats))
    res = service(db, client_factory).sync(account)
    assert res.days == 2  # nightly re-reads only instagram_resync_days
    after = (count(db, AccountDailyStats), count(db, Post), count(db, PostStats), count(db, AudienceStats))
    assert after == before  # unchanged numbers → no duplicate rows / snapshots


def test_small_account_without_audience_still_syncs(db, graph, client_factory, account):
    graph.followers = 50
    res = service(db, client_factory).sync(account)
    assert not res.audience and any("100" in w for w in res.warnings)
    assert count(db, AccountDailyStats) == 5 and count(db, Post) == 2


def test_revoked_token_stops_sync_with_auth_error(db, graph, client_factory, account):
    graph.fail_with = (400, {"error": {"message": "Session expired", "type": "OAuthException", "code": 190}})
    with pytest.raises(InstagramAuthError):
        service(db, client_factory).sync(account)
    assert count(db, AccountDailyStats) == 0


def test_expiring_token_warns_and_expired_token_stops(db, client_factory, account):
    account.token_expires_at = NOW + timedelta(days=3)
    assert any("3 օրից" in w for w in service(db, client_factory).sync(account).warnings)
    account.token_expires_at = NOW - timedelta(days=1)
    with pytest.raises(InstagramAuthError):
        service(db, client_factory).sync(account)


def test_missing_insights_permission_keeps_posts(db, graph, client_factory, account):
    graph.no_insights = True
    res = service(db, client_factory).sync(account)
    assert count(db, Post) == 2 and count(db, AccountDailyStats) == 0
    assert any("instagram_manage_insights" in w for w in res.warnings)
    assert sorted(s.likes for s in db.scalars(select(PostStats))) == [20, 50]  # counts come with the media


def test_lost_permission_never_overwrites_known_stats_with_zero(db, graph, client_factory, account):
    service(db, client_factory).sync(account)
    before = count(db, PostStats)
    graph.no_insights = True
    service(db, client_factory).sync(account)
    assert count(db, PostStats) == before
    assert all(s.views == 7 for s in db.scalars(select(PostStats)))


def test_transient_graph_error_is_not_auth_error(graph, client_factory):
    graph.fail_with = (500, {"error": {"message": "try later", "type": "OAuthException", "code": 2}})
    with pytest.raises(InstagramError) as exc:
        client_factory(TOKEN).profile()
    assert not isinstance(exc.value, InstagramAuthError)


def test_demo_account_is_never_synced(db, client_factory):
    user = User(email="d@x", password_hash="!", name="Demo")
    demo = IgAccount(user=user, ig_user_id="demo_ani", username="ani")
    demo.set_access_token("demo")
    db.add(demo)
    db.commit()
    with pytest.raises(InstagramError):
        service(db, client_factory).sync(demo)


def test_parallel_sync_is_refused(db, client_factory, account):
    lock = _lock_for(account.id)
    lock.acquire()
    try:
        with pytest.raises(SyncBusy):
            service(db, client_factory).sync(account)
    finally:
        lock.release()


def test_current_account_prefers_real_over_demo(db, client_factory):
    user = User(email="d@x", password_hash="!", name="Demo")
    demo = IgAccount(user=user, ig_user_id="demo_ani", username="ani")
    demo.set_access_token("demo")
    db.add(demo)
    db.commit()
    assert AnalyticsRepository(db).get_current_account().username == "ani"
    service(db, client_factory).connect("CODE")
    assert AnalyticsRepository(db).get_current_account().username == "real.creator"

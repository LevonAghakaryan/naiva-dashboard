"""Connecting an Instagram account (OAuth) and syncing its data into the analytics tables.

Sync sections (each one commits on its own, so one failing part never loses the others):
  profile → daily account insights → period (unique) insights → posts + post insights
  → audience demographics → online hours.
Insights metrics differ by account size, media type and API version; a metric the API rejects
(error 100) is retried alone and then skipped for the rest of the run instead of failing the sync.
"""
from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from app.integrations.instagram_graph import (
    InstagramAuthError,
    InstagramClient,
    InstagramError,
    InstagramPermissionError,
    InstagramRateLimit,
    InstagramUnsupported,
    Media,
    metric_breakdown,
    metric_values,
    parse_ts,
    utcnow,
)
from app.models import IgAccount
from app.repositories.instagram_repository import DEMO_PREFIX, InstagramRepository
from core.config import settings

log = logging.getLogger(__name__)

DEFAULT_TZ = "Asia/Yerevan"
EXPIRY_WARNING = timedelta(days=10)  # tell the user to reconnect when fewer days are left
PERIODS = (7, 30)  # the API allows ranges up to 30 days; 90 falls back to the daily sum

# Account insights (metric_type=total_value) → account_daily_stats column
DAILY_METRICS = {
    "reach": "reach", "views": "views", "accounts_engaged": "accounts_engaged",
    "total_interactions": "interactions", "likes": "likes", "comments": "comments",
    "saves": "saves", "shares": "shares", "reposts": "reposts",
    # Bio-link taps. (profile_links_taps counts only the address/call/email/SMS buttons.)
    "profile_views": "profile_views", "website_clicks": "link_taps",
}
# Media insights per product type → post_stats column
MEDIA_METRICS = {
    "FEED": {"views": "views", "reach": "reach", "likes": "likes", "comments": "comments",
             "saved": "saves", "shares": "shares", "follows": "follows", "reposts": "reposts"},
    "REELS": {"views": "views", "reach": "reach", "likes": "likes", "comments": "comments",
              "saved": "saves", "shares": "shares", "reposts": "reposts"},
    "STORY": {"views": "views", "reach": "reach", "shares": "shares", "follows": "follows"},
}
AUDIENCE_BREAKDOWNS = ("age", "gender", "city", "country")

_locks: dict[int, threading.Lock] = {}
_locks_guard = threading.Lock()


class InstagramNotConfigured(Exception):
    pass


class InstagramNoAccount(Exception):
    """The user finished the login but shared no (professional) Instagram account."""


class SyncBusy(Exception):
    pass


@dataclass
class SyncResult:
    account_id: int
    username: str
    days: int = 0
    posts: int = 0
    snapshots: int = 0
    audience: bool = False
    online_hours: bool = False
    api_calls: int = 0
    warnings: list[str] = field(default_factory=list)


def _lock_for(account_id: int) -> threading.Lock:
    with _locks_guard:
        return _locks.setdefault(account_id, threading.Lock())


class InstagramService:
    def __init__(self, repo: InstagramRepository,
                 client_factory: Callable[[str, str], InstagramClient] = InstagramClient,
                 now: Callable[[], datetime] = utcnow):
        self.repo = repo
        self.client_factory = client_factory
        self.now = now  # naive UTC
        self._unsupported: set[tuple[str, str]] = set()

    # ================================================================ connect

    def connect(self, code: str) -> list[IgAccount]:
        """OAuth callback: code → token → every Instagram account the user shared."""
        if not settings.instagram_configured:
            raise InstagramNotConfigured("META_APP_ID / META_APP_SECRET / META_CONFIG_ID-ը .env-ում չկա")
        token = self.client_factory("", "").exchange_code(code)
        ids = self.client_factory(token.access_token, "").assigned_accounts()
        if not ids:
            raise InstagramNoAccount("Instagram-ի Professional հաշիվ չի ընտրվել")
        return [self.connect_token(token.access_token, ig_id, token.expires_at) for ig_id in ids]

    def connect_token(self, access_token: str, ig_id: str, expires_at: datetime | None = None) -> IgAccount:
        """Create/update the account for a token we already have (expires_at=None: never expires)."""
        profile = self.client_factory(access_token, ig_id).profile()
        account = self.repo.account_by_ig_id(profile.ig_user_id)
        if account is None:
            user = self.repo.owner_for(profile.ig_user_id, profile.name or profile.username)
            account = IgAccount(user_id=user.id, ig_user_id=profile.ig_user_id, username=profile.username)
            account.set_access_token(access_token)
            self.repo.add_account(account)
        else:
            account.set_access_token(access_token)
        account.token_expires_at = expires_at
        self._apply_profile(account, profile)
        self.repo.commit()
        log.info("Instagram connected: @%s (account %s)", account.username, account.id)
        return account

    def _check_expiry(self, account: IgAccount, res: SyncResult) -> None:
        """System user tokens never expire by default; if the config says otherwise, warn in time."""
        exp = account.token_expires_at
        if exp is None:
            return
        left = exp - self.now()
        if left <= timedelta(0):
            raise InstagramAuthError("Instagram-ի թույլտվության ժամկետն անցել է, միացրեք նորից")
        if left <= EXPIRY_WARNING:
            res.warnings.append(f"թույլտվության ժամկետն անցնում է {left.days} օրից, միացրեք նորից")

    # ================================================================ sync

    def sync(self, account: IgAccount, days: int | None = None) -> SyncResult:
        if account.ig_user_id.startswith(DEMO_PREFIX):
            raise InstagramError("Դեմո հաշիվը Instagram-ի հետ չի sync-վում")
        lock = _lock_for(account.id)
        if not lock.acquire(blocking=False):
            raise SyncBusy("Sync-ն արդեն ընթացքի մեջ է")
        try:
            return self._sync(account, days)
        finally:
            lock.release()

    def _sync(self, account: IgAccount, days: int | None) -> SyncResult:
        res = SyncResult(account.id, account.username)
        client = self.client_factory(account.get_access_token(), account.ig_user_id)
        tz = self._tz(account)
        today = self.now().replace(tzinfo=timezone.utc).astimezone(tz).date()
        if days is None:
            days = settings.instagram_resync_days if account.last_synced_at else settings.instagram_backfill_days
        days = max(1, min(days, 90))

        self._check_expiry(account, res)
        profile = client.profile()  # auth errors surface here, before any partial write
        self._apply_profile(account, profile)
        self.repo.commit()

        sections = [
            ("daily", lambda: self._sync_daily(account, client, tz, today, days, profile.followers, res)),
            ("period", lambda: self._sync_periods(account, client, tz, today)),
            ("posts", lambda: self._sync_posts(account, client, res)),
            ("audience", lambda: self._sync_audience(account, client, today, res)),
            ("online", lambda: self._sync_online(account, client, tz, res)),
        ]
        for name, run in sections:
            try:
                run()
                self.repo.commit()
            except InstagramAuthError:
                self.repo.rollback()
                raise
            except InstagramRateLimit as e:
                self.repo.rollback()
                res.warnings.append(f"{name}: {e}")
                break
            except InstagramError as e:
                self.repo.rollback()
                res.warnings.append(f"{name}: {e}")
                log.warning("instagram sync @%s %s: %s", account.username, name, e)

        # Project convention: last_synced_at is server-local time (like competitors / seed.py).
        account.last_synced_at = datetime.now().replace(microsecond=0)
        self.repo.commit()
        res.api_calls = client.calls
        log.info("instagram sync @%s: %s", account.username, res)
        return res

    # ---------------------------------------------------------------- helpers

    @staticmethod
    def _tz(account: IgAccount) -> ZoneInfo:
        try:
            return ZoneInfo(account.user.timezone or DEFAULT_TZ)
        except Exception:  # noqa: BLE001
            return ZoneInfo(DEFAULT_TZ)

    @staticmethod
    def _apply_profile(account: IgAccount, p) -> None:
        account.username = p.username
        account.profile_pic_url = p.profile_picture_url
        account.followers_count = p.followers
        account.media_count = p.media_count

    @staticmethod
    def _bounds(tz: ZoneInfo, start: date, end: date) -> dict[str, int]:
        """[start 00:00, end+1 00:00) in the user's timezone as unix seconds."""
        since = datetime.combine(start, time.min, tz)
        until = datetime.combine(end + timedelta(days=1), time.min, tz)
        return {"since": int(since.timestamp()), "until": int(until.timestamp())}

    def _metrics(self, client: InstagramClient, kind: str, path: str, metrics: list[str], **params) -> dict:
        """Fetch several metrics in one call; on error 100 fetch them one by one and remember the
        ones the API rejects (only when some other metric worked — otherwise it's this object's problem)."""
        wanted = [m for m in metrics if (kind, m) not in self._unsupported]
        if not wanted:
            return {"data": []}
        try:
            return client.insights(path, wanted, **params)
        except InstagramUnsupported:
            if len(wanted) == 1:
                raise
        merged, rejected = [], []
        for m in wanted:
            try:
                merged += client.insights(path, [m], **params).get("data", [])
            except InstagramUnsupported:
                rejected.append(m)
        if merged:
            self._unsupported.update((kind, m) for m in rejected)
        elif rejected:
            raise InstagramUnsupported(f"{path}: չաջակցվող ցուցանիշներ ({', '.join(rejected)})")
        return {"data": merged}

    # ---------------------------------------------------------------- sections

    def _sync_daily(self, account: IgAccount, client: InstagramClient, tz: ZoneInfo, today: date,
                    days: int, followers_now: int, res: SyncResult) -> None:
        first = today - timedelta(days=days - 1)
        for i in range(days):
            day = first + timedelta(days=i)
            b = self._bounds(tz, day, day)
            totals = metric_values(self._metrics(
                client, "account", account.ig_user_id, list(DAILY_METRICS), period="day", metric_type="total_value", **b))
            split = self._metrics(client, "account_follow_type", account.ig_user_id, ["reach", "follows_and_unfollows"],
                                  period="day", metric_type="total_value", breakdown="follow_type", **b)
            follows = metric_breakdown(split, "follows_and_unfollows")
            reach_by = metric_breakdown(split, "reach")
            values = {col: totals.get(api, 0) for api, col in DAILY_METRICS.items()}
            values["new_follows"] = follows.get("FOLLOWER", 0)
            values["unfollows"] = follows.get("NON_FOLLOWER", 0)
            values["non_follower_reach"] = reach_by.get("NON_FOLLOWER", 0)
            self.repo.upsert_daily(account.id, day, values)
            res.days += 1

        # Followers is a level: today's count from the profile, earlier days by undoing the net flow.
        rows = self.repo.daily_by_day(account.id, first, today)
        level = followers_now
        for i in range(days):
            day = today - timedelta(days=i)
            row = rows.get(day)
            if row is None:
                continue
            row.followers = max(0, level)
            level -= (row.new_follows or 0) - (row.unfollows or 0)

    def _sync_periods(self, account: IgAccount, client: InstagramClient, tz: ZoneInfo, today: date) -> None:
        last = today - timedelta(days=1)  # periods end yesterday (matches AnalyticsService._periods)
        for days in PERIODS:
            for end in (last, last - timedelta(days=days)):  # current + previous period
                b = self._bounds(tz, end - timedelta(days=days - 1), end)
                totals = metric_values(self._metrics(
                    client, "account", account.ig_user_id, ["reach", "accounts_engaged"],
                    period="day", metric_type="total_value", **b))
                split = self._metrics(client, "account_follow_type", account.ig_user_id, ["reach"],
                                      period="day", metric_type="total_value", breakdown="follow_type", **b)
                self.repo.upsert_period(account.id, end, days, {
                    "reach": totals.get("reach", 0),
                    "accounts_engaged": totals.get("accounts_engaged", 0),
                    "non_follower_reach": metric_breakdown(split, "reach").get("NON_FOLLOWER", 0),
                })

    def _sync_posts(self, account: IgAccount, client: InstagramClient, res: SyncResult) -> None:
        items: list[Media] = client.media(settings.instagram_media_limit)
        try:
            items += client.stories()  # stories live 24 h; insights only while they're live
        except InstagramError as e:
            if isinstance(e, InstagramAuthError):
                raise
            res.warnings.append(f"stories: {e}")
        no_insights = 0
        for m in items:
            post = self.repo.upsert_post(
                account.id, m.ig_media_id, type=m.type, caption=m.caption,
                permalink=m.permalink, thumbnail_url=m.thumbnail_url, posted_at=m.posted_at)
            res.posts += 1
            mapping = MEDIA_METRICS[m.product_type]
            try:
                got = metric_values(self._metrics(client, f"media_{m.product_type}", m.ig_media_id, list(mapping)))
            except InstagramUnsupported as e:  # e.g. posted before the switch to a professional account
                got = {}
                log.info("no insights for media %s: %s", m.ig_media_id, e)
            except InstagramPermissionError as e:  # no insights permission / story with too few viewers
                got = {}
                no_insights += 1
                log.info("insights not permitted for media %s: %s", m.ig_media_id, e)
            # a metric that didn't come is left out: the last known value stays (never overwritten with 0)
            values = {col: got[api] for api, col in mapping.items() if api in got}
            # like/comment counts from the media object are fresher and exist even without insights
            if m.likes is not None:
                values["likes"] = m.likes
            if m.comments is not None:
                values["comments"] = m.comments
            if self.repo.add_post_stats(post, values):
                res.snapshots += 1
        if no_insights:
            res.warnings.append(f"posts: {no_insights} պոստի insights-ը հասանելի չէ (instagram_manage_insights)")

    def _sync_audience(self, account: IgAccount, client: InstagramClient, today: date, res: SyncResult) -> None:
        """follower_demographics needs 100+ followers; below that the API answers error 100."""
        fetched = {}
        for b in AUDIENCE_BREAKDOWNS:
            try:
                data = client.insights(account.ig_user_id, ["follower_demographics"], period="lifetime",
                                       metric_type="total_value", breakdown=b)
            except InstagramUnsupported as e:
                res.warnings.append(f"audience: {e} (պետք է առնվազն 100 հետևորդ)")
                return
            fetched[b] = metric_breakdown(data, "follower_demographics")
        if not any(fetched.values()):
            return
        for b, counts in fetched.items():
            self.repo.replace_audience(account.id, today, b, counts)
        res.audience = True

    def _sync_online(self, account: IgAccount, client: InstagramClient, tz: ZoneInfo, res: SyncResult) -> None:
        try:
            entries = client.online_followers()
        except InstagramUnsupported as e:
            res.warnings.append(f"online hours: {e}")
            return
        sums: dict[tuple[int, int], int] = {}
        counts: dict[tuple[int, int], int] = {}
        for entry in entries:
            hours = entry.get("value")
            if not isinstance(hours, dict) or not hours or not entry.get("end_time"):
                continue
            day_start = parse_ts(entry["end_time"]) - timedelta(days=1)  # end_time closes the 24 h window
            for h, v in hours.items():
                local = (day_start + timedelta(hours=int(h))).replace(tzinfo=timezone.utc).astimezone(tz)
                key = (local.weekday(), local.hour)
                sums[key] = sums.get(key, 0) + int(v or 0)
                counts[key] = counts.get(key, 0) + 1
        if not sums:
            return
        self.repo.replace_online_hours(account.id, {k: round(sums[k] / counts[k]) for k in sums})
        res.online_hours = True

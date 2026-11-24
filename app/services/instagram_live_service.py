"""Live, read-only Instagram data for the /instagram page — straight from the Graph API, no DB.

The token comes only from get_instagram_credentials() (today .env, later the DB per user) and never
leaves the server. Successful answers are cached for CACHE_TTL seconds; errors are never cached.
Insights degrade instead of failing: a metric the API rejects (error 100) is dropped and the rest
retried one by one; a missing permission (error 10) turns the block into "not available" + reason.
"""
from __future__ import annotations

import threading
import time
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from app.integrations.instagram_graph import (
    InstagramClient,
    InstagramCredentials,
    InstagramError,
    InstagramPermissionError,
    InstagramUnsupported,
    get_instagram_credentials,
)

CACHE_TTL = 300  # 5 minutes
MAX_RANGE_DAYS = 30  # the API allows at most ~30 days per insights request

ACCOUNT_METRICS = ["reach", "views", "accounts_engaged", "total_interactions", "likes", "comments",
                   "shares", "saves", "profile_views", "profile_links_taps"]
MEDIA_METRICS = {
    "FEED": ["reach", "views", "likes", "comments", "shares", "saved", "total_interactions"],
    "REELS": ["reach", "views", "likes", "comments", "shares", "saved", "total_interactions"],
    "STORY": ["reach", "views", "shares", "total_interactions"],
}
NO_INSIGHTS_PERMISSION = ("Token-ը չունի instagram_manage_insights թույլտվությունը։ "
                          "Meta-ում ստեղծեք նոր token այդ թույլտվությամբ և դրեք .env-ի INSTAGRAM_ACCESS_TOKEN-ում։")
SMALL_ACCOUNT = "Լսարանի տվյալները հասանելի են 100+ հետևորդից"


class InstagramNotConfigured(Exception):
    pass


class _Cache:
    def __init__(self, ttl: float, clock: Callable[[], float] = time.monotonic):
        self.ttl, self.clock = ttl, clock
        self._data: dict[tuple, tuple[float, object]] = {}
        self._lock = threading.Lock()

    def get(self, key: tuple):
        with self._lock:
            hit = self._data.get(key)
            if hit and self.clock() - hit[0] < self.ttl:
                return hit[1]
            return None

    def put(self, key: tuple, value) -> None:
        with self._lock:
            self._data[key] = (self.clock(), value)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


_cache = _Cache(CACHE_TTL)


def _num(v) -> int | None:
    return None if v is None else int(v)


def _metric_map(data: list[dict]) -> dict[str, int]:
    out: dict[str, int] = {}
    for m in data:
        if "total_value" in m:
            out[m["name"]] = int((m["total_value"] or {}).get("value") or 0)
        elif m.get("values"):
            v = m["values"][-1].get("value")
            out[m["name"]] = int(v) if isinstance(v, (int, float)) else 0
    return out


class InstagramLiveService:
    def __init__(self, credentials: Callable[[], InstagramCredentials | None] = get_instagram_credentials,
                 client_factory: Callable[[str, str], InstagramClient] = InstagramClient,
                 cache: _Cache = _cache, now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)):
        creds = credentials()
        if creds is None:
            raise InstagramNotConfigured(
                "Instagram-ը կարգավորված չէ․ .env-ում լրացրեք INSTAGRAM_ACCOUNT_ID-ը և INSTAGRAM_ACCESS_TOKEN-ը "
                "և վերագործարկեք սերվերը։")
        self.creds = creds
        self.client = client_factory(creds.token, creds.ig_id)
        self.cache = cache
        self.now = now

    def _cached(self, key: tuple, load: Callable[[], object], refresh: bool = False):
        key = (self.creds.ig_id, *key)
        if not refresh:
            hit = self.cache.get(key)
            if hit is not None:
                return hit
        value = load()  # an exception here is never cached
        self.cache.put(key, value)
        return value

    # ------------------------------------------------------------ profile & media

    def profile(self, refresh: bool = False) -> dict:
        def load():
            d = self.client.profile_raw()
            return {
                "id": str(d["id"]), "username": d.get("username"), "name": d.get("name"),
                "biography": d.get("biography"), "website": d.get("website"),
                "profile_picture_url": d.get("profile_picture_url"),
                "followers": _num(d.get("followers_count")), "follows": _num(d.get("follows_count")),
                "media_count": _num(d.get("media_count")),
            }
        return self._cached(("profile",), load, refresh)

    def media(self, after: str | None = None, refresh: bool = False) -> dict:
        def load():
            page = self.client.media_page(after)
            items = []
            for m in page["data"]:
                video = m.get("media_type") == "VIDEO"
                items.append({
                    "id": str(m["id"]), "media_type": m.get("media_type"),
                    "product_type": m.get("media_product_type") or "FEED",
                    "caption": m.get("caption"), "permalink": m.get("permalink"),
                    "media_url": m.get("media_url"),
                    # videos/reels: thumbnail_url is the preview; images and carousels: media_url
                    "preview_url": (m.get("thumbnail_url") if video else m.get("media_url")) or m.get("thumbnail_url"),
                    "timestamp": m.get("timestamp"),
                    "likes": _num(m.get("like_count")),  # None when the owner hid likes → "—"
                    "comments": _num(m.get("comments_count")),
                })
            return {"items": items, "after": page["after"]}
        return self._cached(("media", after or ""), load, refresh)

    def comments(self, media_id: str, refresh: bool = False) -> dict:
        def load():
            def one(c: dict) -> dict:
                return {"id": str(c["id"]), "text": c.get("text"), "username": c.get("username"),
                        "timestamp": c.get("timestamp"), "likes": _num(c.get("like_count"))}
            out = []
            for c in self.client.comments(media_id):
                item = one(c)
                item["replies"] = [one(r) for r in ((c.get("replies") or {}).get("data") or [])]
                out.append(item)
            return {"items": out}
        return self._cached(("comments", media_id), load, refresh)

    def media_detail(self, media_id: str, product_type: str, carousel: bool, refresh: bool = False) -> dict:
        product_type = product_type if product_type in MEDIA_METRICS else "FEED"

        def load():
            children = []
            if carousel:
                try:
                    children = [{"id": str(c["id"]), "media_type": c.get("media_type"),
                                 "preview_url": c.get("thumbnail_url") or c.get("media_url")}
                                for c in self.client.children(media_id)]
                except InstagramUnsupported:
                    children = []
            insights = self._insights(media_id, MEDIA_METRICS[product_type])
            return {"children": children, "insights": insights}
        return self._cached(("media_detail", media_id, product_type, carousel), load, refresh)

    # ------------------------------------------------------------ insights

    def _insights(self, path: str, metrics: list[str], **params) -> dict:
        """{"available": bool, "values": {metric: int}, "skipped": [...], "reason": str|None}"""
        try:
            data = self.client.insights(path, metrics, **params).get("data", [])
            return {"available": True, "values": _metric_map(data), "skipped": [], "reason": None}
        except InstagramPermissionError:
            return {"available": False, "values": {}, "skipped": metrics, "reason": NO_INSIGHTS_PERMISSION}
        except InstagramUnsupported:
            pass
        merged, skipped = [], []
        for m in metrics:  # find out which metric the API rejected; keep the rest
            try:
                merged += self.client.insights(path, [m], **params).get("data", [])
            except InstagramUnsupported:
                skipped.append(m)
            except InstagramPermissionError:
                return {"available": False, "values": {}, "skipped": metrics, "reason": NO_INSIGHTS_PERMISSION}
        values = _metric_map(merged)
        return {"available": bool(values), "values": values, "skipped": skipped,
                "reason": None if values else "Այս ցուցանիշները հասանելի չեն"}

    def account_insights(self, days: int = 28, refresh: bool = False) -> dict:
        days = max(1, min(days, MAX_RANGE_DAYS))

        def load():
            until = self.now().replace(hour=0, minute=0, second=0, microsecond=0)
            since = until - timedelta(days=days)
            span = {"since": int(since.timestamp()), "until": int(until.timestamp())}
            totals = self._insights(self.creds.ig_id, ACCOUNT_METRICS, period="day", metric_type="total_value", **span)
            followers = self._follower_series(span)
            audience = self._audience() if totals["available"] else {
                "available": False, "reason": totals["reason"], "country": {}}
            return {"days": days, "since": since.date().isoformat(), "until": until.date().isoformat(),
                    "totals": totals, "follower_count": followers, "audience": audience}
        return self._cached(("account_insights", days), load, refresh)

    def _follower_series(self, span: dict) -> list[dict]:
        try:
            data = self.client.insights(self.creds.ig_id, ["follower_count"], period="day", **span).get("data", [])
        except (InstagramUnsupported, InstagramPermissionError):
            return []
        for m in data:
            if m.get("name") == "follower_count":
                return [{"date": (v.get("end_time") or "")[:10], "value": v.get("value")} for v in m.get("values", [])]
        return []

    def _audience(self) -> dict:
        try:
            data = self.client.insights(self.creds.ig_id, ["follower_demographics"], period="lifetime",
                                        metric_type="total_value", breakdown="country").get("data", [])
        except (InstagramUnsupported, InstagramPermissionError):
            return {"available": False, "reason": SMALL_ACCOUNT, "country": {}}
        counts: dict[str, int] = {}
        for m in data:
            for b in (m.get("total_value") or {}).get("breakdowns", []):
                for r in b.get("results", []):
                    key = str((r.get("dimension_values") or [""])[0])
                    counts[key] = counts.get(key, 0) + int(r.get("value") or 0)
        if not counts:
            return {"available": False, "reason": SMALL_ACCOUNT, "country": {}}
        return {"available": True, "reason": None, "country": dict(sorted(counts.items(), key=lambda kv: -kv[1])[:10])}


__all__ = ["InstagramLiveService", "InstagramNotConfigured", "InstagramError"]

"""Instagram API with Instagram Login — the creator's OWN account (OAuth, profile, media, insights).

Flow (docs: developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login):
  1. authorize_url(state)      → user approves on instagram.com, comes back with ?code=&state=
  2. exchange_code(code)       → short-lived token (1 h) + IG user id
  3. long_lived_token(short)   → 60-day token; refresh_token() extends it (token must be ≥24 h old)
  4. profile / media / *_insights with the long-lived token (host graph.instagram.com)

Security: the app secret and tokens never leave the server, never appear in exceptions or logs
(see _scrub). All network I/O goes through one `transport` function so tests can fake it.
"""
from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from core.config import settings

log = logging.getLogger(__name__)

AUTHORIZE_URL = "https://www.instagram.com/oauth/authorize"
TOKEN_URL = "https://api.instagram.com/oauth/access_token"
GRAPH_HOST = "https://graph.instagram.com"

# Read-only. Messaging/comments scopes are added when those pages are built.
SCOPES = ("instagram_business_basic", "instagram_business_manage_insights")

PROFILE_FIELDS = "user_id,username,name,account_type,profile_picture_url,followers_count,follows_count,media_count"
MEDIA_FIELDS = ("id,caption,media_type,media_product_type,permalink,media_url,thumbnail_url,"
                "timestamp,like_count,comments_count")
PROFESSIONAL_TYPES = {"BUSINESS", "MEDIA_CREATOR", "CREATOR"}

# Graph error codes
_AUTH_CODES = {190, 102, 10, 200}  # invalid/expired token, missing permission
_RATE_CODES = {4, 17, 32, 613}
_INVALID_PARAM = 100

# (method, url, form-or-None, timeout) → (http status, body bytes)
Transport = Callable[[str, str, dict | None, float], tuple[int, bytes]]


class InstagramError(Exception):
    """Base error. The message is safe to show to the user (no tokens)."""

    def __init__(self, message: str, code: int | None = None):
        super().__init__(message)
        self.code = code


class InstagramAuthError(InstagramError):
    """Token expired/revoked or permission missing → the user must reconnect."""


class InstagramRateLimit(InstagramError):
    """Too many calls; try again later."""


class InstagramUnsupported(InstagramError):
    """A metric/parameter is not available for this account or media (error 100)."""


# ---------------------------------------------------------------- transport

def urllib_transport(method: str, url: str, form: dict | None, timeout: float) -> tuple[int, bytes]:
    data = urllib.parse.urlencode(form).encode() if form is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def _scrub(text: str, *secrets: str) -> str:
    for s in secrets:
        if s:
            text = text.replace(s, "***")
    return text


# ---------------------------------------------------------------- data

@dataclass
class TokenInfo:
    access_token: str
    expires_at: datetime | None  # naive UTC
    ig_user_id: str | None = None


@dataclass
class Profile:
    ig_user_id: str
    username: str
    name: str | None
    account_type: str | None
    profile_picture_url: str | None
    followers: int
    follows: int
    media_count: int


@dataclass
class Media:
    ig_media_id: str
    type: str  # 'reels' | 'carousel' | 'post' | 'story'
    product_type: str  # FEED | REELS | STORY (insights metrics depend on it)
    caption: str | None
    permalink: str | None
    thumbnail_url: str | None
    posted_at: datetime  # naive UTC
    likes: int | None
    comments: int | None


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def parse_ts(value: str) -> datetime:
    """'2026-11-10T12:00:00+0000' → naive UTC datetime (the DB stores naive UTC)."""
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S%z").astimezone(timezone.utc).replace(tzinfo=None)


def media_type(item: dict, story: bool = False) -> str:
    if story or item.get("media_product_type") == "STORY":
        return "story"
    if item.get("media_product_type") == "REELS":
        return "reels"
    if item.get("media_type") == "CAROUSEL_ALBUM":
        return "carousel"
    return "post"


def _media(item: dict, story: bool = False) -> Media:
    kind = media_type(item, story)
    # Videos have thumbnail_url; images only media_url.
    thumb = item.get("thumbnail_url") or (item.get("media_url") if item.get("media_type") != "VIDEO" else None)
    return Media(
        ig_media_id=str(item["id"]), type=kind,
        product_type="STORY" if kind == "story" else ("REELS" if kind == "reels" else "FEED"),
        caption=item.get("caption"), permalink=item.get("permalink"), thumbnail_url=thumb,
        posted_at=parse_ts(item["timestamp"]),
        likes=_opt_int(item.get("like_count")), comments=_opt_int(item.get("comments_count")),
    )


def _opt_int(v) -> int | None:
    return None if v is None else int(v)


def metric_values(data: dict) -> dict[str, int]:
    """Insights response → {metric: value}. Handles both `total_value` and `values[]` shapes."""
    out: dict[str, int] = {}
    for m in data.get("data", []):
        if "total_value" in m:
            out[m["name"]] = int(m["total_value"].get("value") or 0)
        elif m.get("values"):
            v = m["values"][-1].get("value")
            out[m["name"]] = int(v) if isinstance(v, (int, float)) else 0
    return out


def metric_breakdown(data: dict, name: str) -> dict[str, int]:
    """One metric's breakdown results → {dimension value: count} (first dimension only)."""
    for m in data.get("data", []):
        if m.get("name") != name:
            continue
        out: dict[str, int] = {}
        for b in (m.get("total_value") or {}).get("breakdowns", []):
            for r in b.get("results", []):
                key = str((r.get("dimension_values") or [""])[0])
                out[key] = out.get(key, 0) + int(r.get("value") or 0)
        return out
    return {}


# ---------------------------------------------------------------- client

class InstagramClient:
    """One instance per access token (or without a token for the OAuth steps)."""

    def __init__(self, access_token: str = "", *, transport: Transport | None = None,
                 timeout: float = 20, retries: int = 2, sleep: Callable[[float], None] = time.sleep):
        self.token = access_token
        self.transport = transport or urllib_transport
        self.timeout = timeout
        self.retries = retries
        self.sleep = sleep
        self.calls = 0  # for logs / rate awareness

    # ---------- low level

    def _request(self, method: str, url: str, form: dict | None = None) -> dict:
        secrets = (self.token, settings.instagram_app_secret, (form or {}).get("code", ""))
        last: Exception | None = None
        for attempt in range(self.retries + 1):
            self.calls += 1
            try:
                status, body = self.transport(method, url, form, self.timeout)
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                last = InstagramError(f"Instagram API-ն հասանելի չէ ({_scrub(str(e), *secrets)})")
            else:
                try:
                    payload = json.loads(body.decode("utf-8") or "{}")
                except ValueError:
                    payload = {}
                if status < 400 and "error" not in payload:
                    return payload
                last = self._error(status, payload, secrets)
                if status < 500:  # only server errors and network failures are retried
                    raise last
            if attempt < self.retries:
                self.sleep(2 ** attempt)
        assert last is not None
        raise last

    @staticmethod
    def _error(status: int, payload: dict, secrets: tuple[str, ...]) -> InstagramError:
        err = payload.get("error") or {}
        if isinstance(err, str):  # OAuth endpoint shape: {"error_type":..., "error_message":...}
            err = {"message": payload.get("error_message") or err}
        code = err.get("code") or payload.get("code")
        msg = _scrub(str(err.get("message") or payload.get("error_message") or f"HTTP {status}"), *secrets)
        if code in _RATE_CODES:
            return InstagramRateLimit(f"Instagram API-ի հարցումների սահմանը լրացավ ({msg})", code)
        if code == _INVALID_PARAM:
            return InstagramUnsupported(msg, code)
        if code in _AUTH_CODES or err.get("type") == "OAuthException" or status in (401, 403):
            return InstagramAuthError(f"Instagram-ի թույլտվությունը վավեր չէ, միացրեք նորից ({msg})", code)
        return InstagramError(f"Instagram API-ի սխալ ({msg})", code)

    def _get(self, path: str, **params) -> dict:
        params["access_token"] = self.token
        url = f"{GRAPH_HOST}/{settings.graph_api_version}/{path}?{urllib.parse.urlencode(params)}"
        return self._request("GET", url)

    # ---------- OAuth

    @staticmethod
    def authorize_url(state: str) -> str:
        return AUTHORIZE_URL + "?" + urllib.parse.urlencode({
            "client_id": settings.instagram_app_id,
            "redirect_uri": settings.instagram_redirect_uri,
            "response_type": "code",
            "scope": ",".join(SCOPES),
            "state": state,
            "enable_fb_login": "0",
            "force_reauth": "true",
        })

    def exchange_code(self, code: str) -> TokenInfo:
        code = code.removesuffix("#_")  # Instagram appends "#_" to the redirect
        data = self._request("POST", TOKEN_URL, {
            "client_id": settings.instagram_app_id,
            "client_secret": settings.instagram_app_secret,
            "grant_type": "authorization_code",
            "redirect_uri": settings.instagram_redirect_uri,
            "code": code,
        })
        row = (data.get("data") or [data])[0]
        if not row.get("access_token"):
            raise InstagramError("Instagram-ը token չվերադարձրեց")
        return TokenInfo(row["access_token"], None, str(row.get("user_id") or "") or None)

    def long_lived_token(self, short_token: str) -> TokenInfo:
        url = f"{GRAPH_HOST}/access_token?" + urllib.parse.urlencode({
            "grant_type": "ig_exchange_token",
            "client_secret": settings.instagram_app_secret,
            "access_token": short_token,
        })
        self.token = short_token  # so it's scrubbed from errors
        return self._token_info(self._request("GET", url))

    def refresh_token(self) -> TokenInfo:
        url = f"{GRAPH_HOST}/refresh_access_token?" + urllib.parse.urlencode({
            "grant_type": "ig_refresh_token", "access_token": self.token,
        })
        return self._token_info(self._request("GET", url))

    @staticmethod
    def _token_info(data: dict) -> TokenInfo:
        if not data.get("access_token"):
            raise InstagramError("Instagram-ը token չվերադարձրեց")
        expires = data.get("expires_in")
        at = utcnow() + timedelta(seconds=int(expires)) if expires else None
        return TokenInfo(data["access_token"], at)

    # ---------- profile & media

    def profile(self) -> Profile:
        d = self._get("me", fields=PROFILE_FIELDS)
        return Profile(
            ig_user_id=str(d.get("user_id") or d["id"]), username=d["username"], name=d.get("name"),
            account_type=d.get("account_type"), profile_picture_url=d.get("profile_picture_url"),
            followers=int(d.get("followers_count") or 0), follows=int(d.get("follows_count") or 0),
            media_count=int(d.get("media_count") or 0),
        )

    def media(self, limit: int) -> list[Media]:
        out: list[Media] = []
        data = self._get("me/media", fields=MEDIA_FIELDS, limit=min(limit, 100))
        while True:
            out += [_media(m) for m in data.get("data", [])]
            nxt = (data.get("paging") or {}).get("next")
            if len(out) >= limit or not nxt:
                return out[:limit]
            data = self._request("GET", nxt)

    def stories(self) -> list[Media]:
        data = self._get("me/stories", fields=MEDIA_FIELDS)
        return [_media(m, story=True) for m in data.get("data", [])]

    # ---------- insights

    def insights(self, path: str, metrics: list[str], **params) -> dict:
        return self._get(f"{path}/insights", metric=",".join(metrics), **params)

    def online_followers(self) -> list[dict]:
        """[{'end_time': ..., 'value': {'0': n, …, '23': n}}, …] — up to the last 30 days."""
        data = self._get("me/insights", metric="online_followers", period="lifetime")
        for m in data.get("data", []):
            if m.get("name") == "online_followers":
                return list(m.get("values") or [])
        return []

"""Instagram API with Unified login — the creator's OWN account (OAuth, profile, media, insights).

Flow (docs: developers.facebook.com/documentation/instagram-platform/instagram-api-with-unified-login):
  1. authorize_url(state)   → user approves on facebook.com, comes back with ?code=&state=
  2. exchange_code(code)    → Business Integration System User token (never expires by default)
  3. assigned_accounts()    → Instagram accounts the user shared with the app
  4. profile / media / insights on graph.facebook.com/{ig account id}/… — with this kind of token
     "me" is the system user, NOT the Instagram account, so the id is always in the path.

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

AUTHORIZE_HOST = "https://www.facebook.com"
GRAPH_HOST = "https://graph.facebook.com"

# Permissions live in the login configuration (META_CONFIG_ID), not in the URL.
PROFILE_FIELDS = "id,username,name,profile_picture_url,followers_count,follows_count,media_count"
MEDIA_FIELDS = ("id,caption,media_type,media_product_type,permalink,media_url,thumbnail_url,"
                "timestamp,like_count,comments_count")

# Graph error codes
_AUTH_CODES = {190, 102}  # invalid/expired token
_PERMISSION_CODES = {3, 10, *range(200, 300)}  # permission missing (or too few story viewers: 10)
_RATE_CODES = {4, 17, 32, 613, 80002}
_INVALID_PARAM = 100

# (method, url, form-or-None, timeout) → (http status, body bytes)
Transport = Callable[[str, str, dict | None, float], tuple[int, bytes]]


class InstagramError(Exception):
    """Base error. The message is safe to show to the user (no tokens)."""

    def __init__(self, message: str, code: int | None = None):
        super().__init__(message)
        self.code = code


class InstagramAuthError(InstagramError):
    """Token expired/revoked → the user must reconnect."""


class InstagramPermissionError(InstagramError):
    """The token is fine, but it lacks the permission for this one call → skip it, keep the rest."""


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
    expires_at: datetime | None  # naive UTC; None = never expires


@dataclass
class Profile:
    ig_user_id: str
    username: str
    name: str | None
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
    """One instance per access token + Instagram account id (both empty for the OAuth step)."""

    def __init__(self, access_token: str = "", account_id: str = "", *, transport: Transport | None = None,
                 timeout: float = 20, retries: int = 2, sleep: Callable[[float], None] = time.sleep):
        self.token = access_token
        self.account_id = account_id
        self.transport = transport or urllib_transport
        self.timeout = timeout
        self.retries = retries
        self.sleep = sleep
        self.calls = 0  # for logs / rate awareness

    # ---------- low level

    def _request(self, method: str, url: str, form: dict | None = None, hide: tuple[str, ...] = ()) -> dict:
        secrets = (self.token, settings.meta_app_secret, *hide)
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
        if code in _PERMISSION_CODES:
            return InstagramPermissionError(f"թույլտվությունը բացակայում է ({msg})", code)
        # Almost every Graph error has type OAuthException, so the type counts only without a code.
        if code in _AUTH_CODES or (code is None and err.get("type") == "OAuthException") or status in (401, 403):
            return InstagramAuthError(f"Instagram-ի թույլտվությունը վավեր չէ, միացրեք նորից ({msg})", code)
        return InstagramError(f"Instagram API-ի սխալ ({msg})", code)

    def _get(self, path: str, **params) -> dict:
        params["access_token"] = self.token
        url = f"{GRAPH_HOST}/{settings.graph_api_version}/{path}?{urllib.parse.urlencode(params)}"
        return self._request("GET", url)

    # ---------- OAuth

    @staticmethod
    def authorize_url(state: str) -> str:
        return f"{AUTHORIZE_HOST}/{settings.graph_api_version}/dialog/oauth?" + urllib.parse.urlencode({
            "client_id": settings.meta_app_id,
            "config_id": settings.meta_config_id,
            "redirect_uri": settings.instagram_redirect_uri,
            "response_type": "code",
            "prompt": "login",  # always offer both the Facebook and the Instagram login
            "state": state,
        })

    def exchange_code(self, code: str) -> TokenInfo:
        code = code.removesuffix("#_")
        url = f"{GRAPH_HOST}/{settings.graph_api_version}/oauth/access_token?" + urllib.parse.urlencode({
            "client_id": settings.meta_app_id,
            "client_secret": settings.meta_app_secret,
            "code": code,
        })
        data = self._request("GET", url, hide=(code,))
        if not data.get("access_token"):
            raise InstagramError("Meta-ն token չվերադարձրեց")
        expires = data.get("expires_in")
        at = utcnow() + timedelta(seconds=int(expires)) if expires else None
        return TokenInfo(data["access_token"], at)

    def assigned_accounts(self) -> list[str]:
        """Ids of the Instagram accounts the user shared with the app."""
        data = self._get("me/assigned_instagram_accounts", fields="id,username", limit=100)
        return [str(a["id"]) for a in data.get("data", [])]

    # ---------- profile & media

    def profile(self) -> Profile:
        d = self._get(self.account_id, fields=PROFILE_FIELDS)
        return Profile(
            ig_user_id=str(d["id"]), username=d["username"], name=d.get("name"),
            profile_picture_url=d.get("profile_picture_url"),
            followers=int(d.get("followers_count") or 0), follows=int(d.get("follows_count") or 0),
            media_count=int(d.get("media_count") or 0),
        )

    def media(self, limit: int) -> list[Media]:
        out: list[Media] = []
        data = self._get(f"{self.account_id}/media", fields=MEDIA_FIELDS, limit=min(limit, 100))
        while True:
            out += [_media(m) for m in data.get("data", [])]
            nxt = (data.get("paging") or {}).get("next")
            if len(out) >= limit or not nxt:
                return out[:limit]
            data = self._request("GET", nxt)

    def stories(self) -> list[Media]:
        data = self._get(f"{self.account_id}/stories", fields=MEDIA_FIELDS)
        return [_media(m, story=True) for m in data.get("data", [])]

    # ---------- insights

    def insights(self, path: str, metrics: list[str], **params) -> dict:
        return self._get(f"{path}/insights", metric=",".join(metrics), **params)

    def online_followers(self) -> list[dict]:
        """[{'end_time': ..., 'value': {'0': n, …, '23': n}}, …] — up to the last 30 days."""
        data = self._get(f"{self.account_id}/insights", metric="online_followers", period="lifetime")
        for m in data.get("data", []):
            if m.get("name") == "online_followers":
                return list(m.get("values") or [])
        return []

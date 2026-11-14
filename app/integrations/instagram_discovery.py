"""Instagram Graph API — Business Discovery (public data of another Business/Creator account).

Everything this endpoint can return is requested. It does NOT return insights (reach, saves,
shares, profile visits, audience) — only the account owner can read those.
Docs: developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/business_discovery

  GET /{our-ig-user-id}?fields=business_discovery.username(<handle>){...}&access_token=<our token>
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime

from core.config import settings

PROFILE_FIELDS = "id,username,name,biography,website,profile_picture_url,followers_count,follows_count,media_count"
MEDIA_FIELDS = ("id,caption,like_count,comments_count,view_count,media_type,media_product_type,"
                "permalink,media_url,thumbnail_url,timestamp")
MEDIA_LIMIT = 50  # newest posts per sync; 90 days of a typical account fit


class DiscoveryError(Exception):
    """The account doesn't exist, isn't Business/Creator, is age-gated, or the API failed."""


@dataclass
class DiscoveredPost:
    ig_media_id: str
    type: str  # 'reels' | 'carousel' | 'post'
    caption: str | None
    permalink: str | None
    media_url: str | None
    thumbnail_url: str | None
    likes: int | None  # None when the owner hides like counts
    comments: int
    views: int | None
    posted_at: datetime


@dataclass
class DiscoveredAccount:
    ig_user_id: str
    username: str
    name: str | None
    biography: str | None
    website: str | None
    profile_picture_url: str | None
    followers: int
    follows: int | None
    media_count: int
    posts: list[DiscoveredPost] = field(default_factory=list)


def _post_type(item: dict) -> str:
    if item.get("media_product_type") == "REELS":
        return "reels"
    if item.get("media_type") == "CAROUSEL_ALBUM":
        return "carousel"
    return "post"


def _int(v) -> int | None:
    return None if v is None else int(v)


def parse(data: dict) -> DiscoveredAccount:
    bd = data.get("business_discovery")
    if not bd:
        raise DiscoveryError("Business Discovery-ն պատասխան չտվեց")
    posts = []
    for m in (bd.get("media") or {}).get("data", []):
        # "2026-11-10T12:00:00+0000" → naive UTC datetime (DB stores naive)
        ts = datetime.strptime(m["timestamp"], "%Y-%m-%dT%H:%M:%S%z").replace(tzinfo=None)
        posts.append(DiscoveredPost(
            ig_media_id=str(m["id"]), type=_post_type(m), caption=m.get("caption"),
            permalink=m.get("permalink"), media_url=m.get("media_url"), thumbnail_url=m.get("thumbnail_url"),
            likes=_int(m.get("like_count")), comments=int(m.get("comments_count") or 0),
            views=_int(m.get("view_count")), posted_at=ts,
        ))
    return DiscoveredAccount(
        ig_user_id=str(bd["id"]), username=bd["username"], name=bd.get("name"),
        biography=bd.get("biography"), website=bd.get("website"),
        profile_picture_url=bd.get("profile_picture_url"),
        followers=int(bd.get("followers_count") or 0), follows=_int(bd.get("follows_count")),
        media_count=int(bd.get("media_count") or 0), posts=posts,
    )


def fetch(our_ig_user_id: str, access_token: str, username: str, timeout: float = 15) -> DiscoveredAccount:
    fields = (f"business_discovery.username({username})"
              f"{{{PROFILE_FIELDS},media.limit({MEDIA_LIMIT}){{{MEDIA_FIELDS}}}}}")
    query = urllib.parse.urlencode({"fields": fields, "access_token": access_token})
    url = f"https://graph.facebook.com/{settings.graph_api_version}/{our_ig_user_id}?{query}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return parse(json.loads(resp.read().decode("utf-8")))
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read().decode("utf-8"))["error"]["message"]
        except Exception:  # noqa: BLE001
            msg = f"HTTP {e.code}"
        raise DiscoveryError(f"@{username}: հաշիվը չգտնվեց կամ Business/Creator չէ ({msg})") from e
    except (urllib.error.URLError, TimeoutError) as e:
        raise DiscoveryError(f"Instagram API-ն հասանելի չէ ({e})") from e

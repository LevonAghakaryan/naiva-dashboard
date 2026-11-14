"""Response shapes for /api/competitors/* (the "Մրցակիցներ" page).

Numbers are raw; ranking, group average, % vs average and head-to-head are computed in the browser.
Only public data (Instagram Business Discovery) is compared, the same way for "you" and competitors.
"""
import re
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Period = Literal[7, 30, 90]
CompetitorPostType = Literal["post", "carousel", "reels"]

METRIC_KEYS = ("followers", "er", "posts", "likes", "comments", "views")


class Metrics(BaseModel):
    followers: int
    er: float = Field(description="(likes + comments) / followers × 100, average per post in the period")
    posts: float = Field(description="posts per week in the period")
    likes: float = Field(description="average likes per post (posts with hidden likes are skipped)")
    comments: float
    views: float = Field(description="average views per post that has a view count")


class Participant(BaseModel):
    id: int | None  # None = you
    handle: str
    name: str | None
    is_me: bool
    color: str
    avatar_url: str | None
    biography: str | None
    website: str | None
    follows: int | None
    media_count: int | None
    followers_delta: int | None = Field(description="followers change over the period (from daily snapshots)")
    post_count: int  # posts in the period
    has_data: bool  # False: added but not synced yet
    last_synced_at: datetime | None
    sync_error: str | None
    metrics: Metrics


class CompetitorPostOut(BaseModel):
    id: int
    competitor_id: int
    handle: str
    color: str
    type: CompetitorPostType
    caption: str | None
    permalink: str | None
    image_url: str | None
    posted_at: datetime
    likes: int | None
    comments: int
    views: int | None
    er: float | None  # (likes + comments) / followers × 100
    er_good: bool | None  # ER ≥ average ER of the listed posts


class CompetitorsPageOut(BaseModel):
    days: Period
    start: date
    end: date
    max_competitors: int
    sync_enabled: bool
    participants: list[Participant]  # you first, then competitors in the order they were added
    posts: list[CompetitorPostOut]  # competitors' posts in the period, newest first
    avg_post_er: float | None


class CompetitorIn(BaseModel):
    username: str = Field(examples=["lilit.style", "@lilit.style", "https://instagram.com/lilit.style/"])

    @field_validator("username")
    @classmethod
    def _clean(cls, v: str) -> str:
        v = v.strip()
        m = re.search(r"instagram\.com/([A-Za-z0-9._]+)", v)
        if m:
            v = m.group(1)
        v = v.lstrip("@").strip().strip("/").lower()
        if not re.fullmatch(r"[a-z0-9._]{1,30}", v):
            raise ValueError("Անվավեր Instagram handle (թույլատրված են տառեր, թվեր, «.» և «_», մինչև 30 նիշ)")
        return v

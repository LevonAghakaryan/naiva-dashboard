"""Response shapes for /api/analytics/* (the "Instagram վիճակագրություն" page, instagram-spec.md).

Numbers are sent raw; the frontend formats them (48,214 → 48.2K, 7.9%).
"""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Period = Literal[7, 30, 90]
PostType = Literal["post", "carousel", "reels", "story"]
Granularity = Literal["day", "week"]
DeltaUnit = Literal["pct", "pp", "abs"]


# ---------- GET /api/analytics/page ----------

class Bucket(BaseModel):
    """One chart point: a day (start == end) or a week (up to 7 days)."""
    start: date
    end: date


class MetricOut(BaseModel):
    key: str = Field(examples=["likes"])
    label: str = Field(examples=["Likes"])  # Instagram term, stays in English
    kind: Literal["flow", "level"]  # flow = summed per day; level = a value at a moment (followers, %)
    unit: Literal["count", "pct"]
    value: float  # period total (flow) or current value (level)
    previous: float | None  # same-length period right before; None when there is no data
    delta: float | None = Field(description="pct: % change; pp: percentage points; abs: net change")
    delta_unit: DeltaUnit
    good: bool | None  # green pill if True; Unfollows growth is bad
    gran: Granularity  # which bucket list `points` follows
    points: list[float]  # oldest → newest
    prev_points: list[float] | None  # previous period aligned by index (only 7/30 days, flows)


class PostRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    caption: str | None
    thumbnail_url: str | None
    permalink: str | None
    type: PostType
    posted_at: datetime
    views: int
    reach: int
    likes: int
    comments: int
    saves: int
    shares: int
    reposts: int
    follows: int
    er: float  # (likes + comments + saves + shares) / reach × 100, one decimal


class PageOut(BaseModel):
    username: str
    last_synced_at: datetime | None  # "թարմացվել է 15 րոպե առաջ"
    days: Period
    period_start: date
    period_end: date
    has_previous: bool
    day_buckets: list[Bucket]
    week_buckets: list[Bucket]  # 90 days → 13 weeks (the oldest may be shorter)
    hero: list[str]  # metric keys in display order
    grid: list[str]  # 12 metric keys in display order
    metrics: dict[str, MetricOut]
    posts: list[PostRow]  # posts of the period, newest first (stories excluded)


# ---------- GET /api/analytics/posts?month=YYYY-MM ----------

class MonthPostsOut(BaseModel):
    month: str = Field(examples=["2026-11"])
    first_month: str | None  # oldest month with posts (calendar ← stops there)
    posts: list[PostRow]


# ---------- GET /api/analytics/audience ----------

class ShareItem(BaseModel):
    key: str = Field(examples=["F", "25-34", "Yerevan"])
    label: str = Field(examples=["Կանայք", "25–34", "Երևան"])
    percent: float  # 0–100, one decimal


class AudienceOut(BaseModel):
    as_of: date | None  # snapshot day; None when there is no data yet
    gender: list[ShareItem]  # Կանայք / Տղամարդիկ
    age: list[ShareItem]  # 13–17, 18–24, 25–34, 35–44, 45+
    cities: list[ShareItem]  # top 5
    countries: list[ShareItem]  # top 5


# ---------- GET /api/analytics/active-hours ----------

class BestTime(BaseModel):
    days: list[int]  # weekday indexes, 0 = Երկ … 6 = Կիր
    days_label: str = Field(examples=["Երք–Հնգ"])
    start_hour: int
    end_hour: int
    hours_label: str = Field(examples=["19:00–21:00"])


class ActiveHoursOut(BaseModel):
    day_labels: list[str]  # ["Երկ", "Երք", "Չրք", "Հնգ", "Ուրբ", "Շբթ", "Կիր"]
    slot_labels: list[str]  # 8 two-hour slots: ["09", "11", …, "23"]
    grid: list[list[int]]  # grid[day][slot] = online followers
    max_value: int  # for heatmap color scale
    best: BestTime | None

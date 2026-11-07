"""Response shapes for /api/analytics/* (the "Instagram վիճակագրություն" page).

Numbers are sent raw; the frontend formats them (48,230 → 48.2K, ֏, %).
"""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Page tabs: Ընդհանուր / Reels / Posts / Stories. "posts" = post + carousel.
AnalyticsType = Literal["all", "reels", "posts", "stories"]
PostType = Literal["post", "carousel", "reels", "story"]
PostSort = Literal["views", "reach", "likes", "comments", "saves", "shares", "er", "posted_at"]
Direction = Literal["up", "down", "flat"]


# ---------- GET /api/analytics/summary ----------

class KpiItem(BaseModel):
    key: str = Field(examples=["views"])
    label: str = Field(examples=["Views"])  # Armenian UI label, e.g. "Պրոֆիլի դիտումներ"
    value: int
    previous: int  # same-length period right before the current one
    change_pct: float | None = Field(description="None when previous is 0", examples=[14.0])
    direction: Direction


class SummaryOut(BaseModel):
    username: str
    type: AnalyticsType
    days: int
    period_start: date
    period_end: date
    last_synced_at: datetime | None  # "թարմացվել է 15 րոպե առաջ"
    kpis: list[KpiItem]  # always 4, in display order


# ---------- GET /api/analytics/reach-daily ----------

class ReachDay(BaseModel):
    day: date
    label: str = Field(examples=["Նոյ 6"])
    reach: int
    is_max: bool  # highest bar is drawn dark blue


class ReachDailyOut(BaseModel):
    days: int
    total: int
    items: list[ReachDay]  # oldest → newest


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


# ---------- GET /api/analytics/active-hours ----------

class BestTime(BaseModel):
    days: list[int]  # weekday indexes, 0 = Երկ … 6 = Կիր
    days_label: str = Field(examples=["Երք–Հնգ"])
    start_hour: int
    end_hour: int
    hours_label: str = Field(examples=["19:00–21:00"])


class ActiveHoursOut(BaseModel):
    day_labels: list[str]  # ["Երկ", "Երք", "Չրք", "Հնգ", "Ուրբ", "Շբթ", "Կիր"]
    slot_labels: list[str]  # 2-hour slots: ["09", "11", …, "21"]
    grid: list[list[int]]  # grid[day][slot] = online followers
    max_value: int  # for heatmap color scale
    best: BestTime | None


# ---------- GET /api/analytics/posts ----------

class PostRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    caption: str | None
    thumbnail_url: str | None
    permalink: str | None
    type: PostType
    type_label: str = Field(examples=["Reels", "Post", "Carousel", "Story"])
    posted_at: datetime
    views: int
    reach: int
    likes: int
    comments: int
    saves: int
    shares: int
    er: float  # (likes + comments + saves + shares) / reach × 100, one decimal
    er_good: bool  # green pill if True, red if False


class PostsOut(BaseModel):
    type: AnalyticsType
    sort: PostSort
    total: int
    items: list[PostRow]

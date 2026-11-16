"""Response shape for /api/home/page (the "Գլխավոր" dashboard).

Numbers are sent raw; the frontend formats them (48,230 → 48.2K, ֏1.24M).
"""
from datetime import date

from pydantic import BaseModel

from app.schemas.analytics import BestTime, MetricOut, Period, PostRow


class IncomeKpi(BaseModel):
    value: int  # done income of the period
    previous: int  # done income of the same-length period right before
    points: list[int]  # done income per day, oldest → newest


class FinanceMonth(BaseModel):
    month_label: str  # "Նոյեմբեր 2026"
    income: int
    expense: int
    pending_income: int  # pending income of the month (not counted in income)


class NextPayment(BaseModel):
    title: str
    amount: int
    date: date


class Rival(BaseModel):
    handle: str
    is_me: bool
    color: str
    followers: int
    er: float


class HomeOut(BaseModel):
    days: Period
    username: str
    user_name: str | None
    period_start: date
    period_end: date
    has_previous: bool
    metrics: dict[str, MetricOut]  # followers, reach, er (same as the analytics page)
    income: IncomeKpi
    finance: FinanceMonth
    next_payment: NextPayment | None  # the nearest pending income
    best_time: BestTime | None
    rivals: list[Rival]  # you + competitors that have data
    top_posts: list[PostRow]  # best 4 by views
    avg_post_er: float | None  # ER average of the period posts (good / weak row color)

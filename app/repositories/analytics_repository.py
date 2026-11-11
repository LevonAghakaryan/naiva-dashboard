"""DB queries for the analytics page. Only SQL here — no percentages, ER or formatting.

Date ranges are inclusive: start <= day <= end.
`types` is a list of raw post types ('post', 'carousel', 'reels', 'story'); None = all.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models import (
    AccountDailyStats,
    AccountPeriodStats,
    AudienceOnlineHours,
    AudienceStats,
    IgAccount,
    Post,
    PostStats,
)


@dataclass(frozen=True)
class AudienceRow:
    breakdown: str
    label: str
    value: int


class AnalyticsRepository:
    def __init__(self, db: Session):
        self.db = db

    # ---------- account ----------

    def get_current_account(self) -> IgAccount | None:
        """Until auth exists, the "current" account is the first one in the DB."""
        return self.db.scalar(select(IgAccount).order_by(IgAccount.id).limit(1))

    # ---------- account_daily_stats ----------

    def daily_rows(self, account_id: int, start: date, end: date) -> list[AccountDailyStats]:
        return list(self.db.scalars(
            select(AccountDailyStats)
            .where(
                AccountDailyStats.ig_account_id == account_id,
                AccountDailyStats.day.between(start, end),
            )
            .order_by(AccountDailyStats.day)
        ))

    def last_followers_before(self, account_id: int, day: date) -> int | None:
        """Followers at the newest snapshot strictly before `day`."""
        return self.db.scalar(
            select(AccountDailyStats.followers)
            .where(AccountDailyStats.ig_account_id == account_id, AccountDailyStats.day < day)
            .order_by(AccountDailyStats.day.desc())
            .limit(1)
        )

    # ---------- account_period_stats ----------

    def period_stats(self, account_id: int, end_day: date, days: int) -> AccountPeriodStats | None:
        return self.db.scalar(
            select(AccountPeriodStats).where(
                AccountPeriodStats.ig_account_id == account_id,
                AccountPeriodStats.end_day == end_day,
                AccountPeriodStats.days == days,
            )
        )

    # ---------- posts + latest post_stats ----------

    def _latest_stats_ids(self, account_id: int):
        """Subquery: id of the newest post_stats snapshot per post of this account."""
        return (
            select(func.max(PostStats.id).label("stats_id"))
            .join(Post, Post.id == PostStats.post_id)
            .where(Post.ig_account_id == account_id)
            .group_by(PostStats.post_id)
            .subquery()
        )

    def _posts_with_latest_stats(self, account_id: int, types: Sequence[str] | None,
                                 start: date | None, end: date | None) -> Select:
        latest = self._latest_stats_ids(account_id)
        stmt = (
            select(Post, PostStats)
            .outerjoin(PostStats, PostStats.post_id == Post.id)
            .where(
                Post.ig_account_id == account_id,
                (PostStats.id.is_(None)) | (PostStats.id.in_(select(latest.c.stats_id))),
            )
        )
        if types:
            stmt = stmt.where(Post.type.in_(types))
        if start is not None:
            stmt = stmt.where(Post.posted_at >= datetime.combine(start, time.min))
        if end is not None:
            stmt = stmt.where(Post.posted_at < datetime.combine(end + timedelta(days=1), time.min))
        return stmt

    def list_posts(self, account_id: int, types: Sequence[str] | None = None,
                   start: date | None = None, end: date | None = None,
                   ) -> list[tuple[Post, PostStats | None]]:
        """Posts with their newest snapshot, newest post first."""
        stmt = self._posts_with_latest_stats(account_id, types, start, end).order_by(Post.posted_at.desc())
        return [(r[0], r[1]) for r in self.db.execute(stmt).all()]

    def first_post_at(self, account_id: int, types: Sequence[str] | None = None) -> datetime | None:
        stmt = select(func.min(Post.posted_at)).where(Post.ig_account_id == account_id)
        if types:
            stmt = stmt.where(Post.type.in_(types))
        return self.db.scalar(stmt)

    # ---------- audience ----------

    def latest_audience(self, account_id: int) -> tuple[date | None, list[AudienceRow]]:
        as_of = self.db.scalar(
            select(func.max(AudienceStats.day)).where(AudienceStats.ig_account_id == account_id)
        )
        if as_of is None:
            return None, []
        rows = self.db.execute(
            select(AudienceStats.breakdown, AudienceStats.label, AudienceStats.value)
            .where(AudienceStats.ig_account_id == account_id, AudienceStats.day == as_of)
            .order_by(AudienceStats.breakdown, AudienceStats.value.desc())
        ).all()
        return as_of, [AudienceRow(r.breakdown, r.label, int(r.value)) for r in rows]

    def online_hours(self, account_id: int) -> list[tuple[int, int, int]]:
        """(weekday 0=Mon…6=Sun, hour 0–23, value)."""
        rows = self.db.execute(
            select(AudienceOnlineHours.day, AudienceOnlineHours.hour, AudienceOnlineHours.value)
            .where(AudienceOnlineHours.ig_account_id == account_id)
            .order_by(AudienceOnlineHours.day, AudienceOnlineHours.hour)
        ).all()
        return [(int(r.day), int(r.hour), int(r.value)) for r in rows]

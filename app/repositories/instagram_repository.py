"""DB writes for the Instagram connection and sync (the analytics tables are read by AnalyticsRepository).

Every write is an idempotent upsert, so re-running a sync for the same days never duplicates rows.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import (
    AccountDailyStats,
    AccountPeriodStats,
    AudienceOnlineHours,
    AudienceStats,
    IgAccount,
    Post,
    PostStats,
    User,
)

DEMO_PREFIX = "demo_"  # scripts/seed.py: demo accounts have ig_user_id "demo_…"

STAT_FIELDS = ("views", "reach", "likes", "comments", "saves", "shares", "reposts", "follows")


class InstagramRepository:
    def __init__(self, db: Session):
        self.db = db

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()

    # ---------- accounts

    def account_by_ig_id(self, ig_user_id: str) -> IgAccount | None:
        return self.db.scalar(select(IgAccount).where(IgAccount.ig_user_id == ig_user_id))

    def get_account(self, account_id: int) -> IgAccount | None:
        return self.db.get(IgAccount, account_id)

    def real_accounts(self) -> list[IgAccount]:
        """Connected (non-demo) accounts, for the nightly job."""
        return list(self.db.scalars(
            select(IgAccount).where(IgAccount.ig_user_id.not_like(f"{DEMO_PREFIX}%")).order_by(IgAccount.id)
        ))

    def owner_for(self, ig_user_id: str, name: str) -> User:
        """Until auth exists, every connected Instagram account gets its own local user.

        It is never the demo user, so `seed.py --reset` (which deletes the demo user) can't
        cascade-delete a real account.
        """
        email = f"ig-{ig_user_id}@creatorly.local"
        user = self.db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(email=email, password_hash="!no-login-yet", name=name[:120])
            self.db.add(user)
            self.db.flush()
        return user

    def add_account(self, account: IgAccount) -> None:
        self.db.add(account)
        self.db.flush()

    # ---------- account_daily_stats / account_period_stats

    def upsert_daily(self, account_id: int, day: date, values: dict[str, int]) -> AccountDailyStats:
        self.db.flush()
        row = self.db.scalar(select(AccountDailyStats).where(
            AccountDailyStats.ig_account_id == account_id, AccountDailyStats.day == day))
        if row is None:
            row = AccountDailyStats(ig_account_id=account_id, day=day)
            self.db.add(row)
        for k, v in values.items():
            setattr(row, k, max(0, int(v)))
        return row

    def daily_by_day(self, account_id: int, start: date, end: date) -> dict[date, AccountDailyStats]:
        self.db.flush()  # SessionLocal has autoflush=False: make rows added in this run visible
        rows = self.db.scalars(select(AccountDailyStats).where(
            AccountDailyStats.ig_account_id == account_id,
            AccountDailyStats.day >= start, AccountDailyStats.day <= end))
        return {r.day: r for r in rows}

    def upsert_period(self, account_id: int, end_day: date, days: int, values: dict[str, int]) -> None:
        self.db.flush()
        row = self.db.scalar(select(AccountPeriodStats).where(
            AccountPeriodStats.ig_account_id == account_id,
            AccountPeriodStats.end_day == end_day, AccountPeriodStats.days == days))
        if row is None:
            row = AccountPeriodStats(ig_account_id=account_id, end_day=end_day, days=days)
            self.db.add(row)
        for k, v in values.items():
            setattr(row, k, max(0, int(v)))

    # ---------- posts / post_stats

    def upsert_post(self, account_id: int, ig_media_id: str, **fields) -> Post:
        post = self.db.scalar(select(Post).where(Post.ig_media_id == ig_media_id))
        if post is None:
            post = Post(ig_account_id=account_id, ig_media_id=ig_media_id, **fields)
            self.db.add(post)
            self.db.flush()
        elif post.ig_account_id != account_id:
            raise ValueError(f"media {ig_media_id} belongs to another account")
        else:
            for k, v in fields.items():
                setattr(post, k, v)
        return post

    def add_post_stats(self, post: Post, values: dict[str, int]) -> bool:
        """Append a snapshot only when something changed since the last one. Returns True if added."""
        self.db.flush()
        clean = {k: max(0, int(values.get(k) or 0)) for k in STAT_FIELDS}
        last = self.db.scalar(
            select(PostStats).where(PostStats.post_id == post.id).order_by(PostStats.id.desc()).limit(1))
        if last is not None and all(getattr(last, k) == v for k, v in clean.items()):
            return False
        self.db.add(PostStats(post_id=post.id, **clean))
        return True

    # ---------- audience

    def replace_audience(self, account_id: int, day: date, breakdown: str, counts: dict[str, int]) -> None:
        self.db.execute(delete(AudienceStats).where(
            AudienceStats.ig_account_id == account_id, AudienceStats.day == day,
            AudienceStats.breakdown == breakdown))
        for label, value in counts.items():
            if label and value > 0:
                self.db.add(AudienceStats(ig_account_id=account_id, day=day, breakdown=breakdown,
                                          label=label[:100], value=int(value)))

    def replace_online_hours(self, account_id: int, grid: dict[tuple[int, int], int]) -> None:
        self.db.execute(delete(AudienceOnlineHours).where(AudienceOnlineHours.ig_account_id == account_id))
        for (day, hour), value in sorted(grid.items()):
            self.db.add(AudienceOnlineHours(ig_account_id=account_id, day=day, hour=hour, value=int(value)))

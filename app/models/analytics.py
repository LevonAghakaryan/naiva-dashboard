"""Instagram analytics tables (block 2 of db/schema.sql)."""
from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.types import BigIntFK, BigIntPK, TinyUInt, UInt
from core.database import Base

if TYPE_CHECKING:
    from app.models.ig_account import IgAccount

POST_TYPES = ("post", "carousel", "reels", "story")
AUDIENCE_BREAKDOWNS = ("age", "gender", "city", "country")


class AccountDailyStats(Base):
    """One snapshot per account per day (Instagram keeps account insights only ~90 days)."""

    __tablename__ = "account_daily_stats"
    __table_args__ = (UniqueConstraint("ig_account_id", "day", name="uq_account_day"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    ig_account_id: Mapped[int] = mapped_column(BigIntFK, ForeignKey("ig_accounts.id", ondelete="CASCADE"))
    day: Mapped[date] = mapped_column(Date)
    followers: Mapped[int] = mapped_column(UInt, default=0, server_default="0")  # level (end of day)
    # Flows for that day:
    new_follows: Mapped[int] = mapped_column(UInt, default=0, server_default="0")
    unfollows: Mapped[int] = mapped_column(UInt, default=0, server_default="0")
    reach: Mapped[int] = mapped_column(UInt, default=0, server_default="0")  # unique accounts that day
    non_follower_reach: Mapped[int] = mapped_column(UInt, default=0, server_default="0")
    views: Mapped[int] = mapped_column(UInt, default=0, server_default="0")
    accounts_engaged: Mapped[int] = mapped_column(UInt, default=0, server_default="0")  # unique that day
    interactions: Mapped[int] = mapped_column(UInt, default=0, server_default="0")
    likes: Mapped[int] = mapped_column(UInt, default=0, server_default="0")
    comments: Mapped[int] = mapped_column(UInt, default=0, server_default="0")
    saves: Mapped[int] = mapped_column(UInt, default=0, server_default="0")
    shares: Mapped[int] = mapped_column(UInt, default=0, server_default="0")
    reposts: Mapped[int] = mapped_column(UInt, default=0, server_default="0")
    profile_views: Mapped[int] = mapped_column(UInt, default=0, server_default="0")
    link_taps: Mapped[int] = mapped_column(UInt, default=0, server_default="0")

    ig_account: Mapped[IgAccount] = relationship(back_populates="daily_stats")


class AccountPeriodStats(Base):
    """Unique-account metrics for a whole period (reach, accounts engaged can't be summed by day).

    One row per (account, last day of the period, period length in days), taken from the API
    for exactly that period. When a row is missing the service falls back to the daily sum.
    """

    __tablename__ = "account_period_stats"
    __table_args__ = (UniqueConstraint("ig_account_id", "end_day", "days", name="uq_account_period"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    ig_account_id: Mapped[int] = mapped_column(BigIntFK, ForeignKey("ig_accounts.id", ondelete="CASCADE"))
    end_day: Mapped[date] = mapped_column(Date)
    days: Mapped[int] = mapped_column(TinyUInt)
    reach: Mapped[int] = mapped_column(UInt, default=0, server_default="0")
    non_follower_reach: Mapped[int] = mapped_column(UInt, default=0, server_default="0")
    accounts_engaged: Mapped[int] = mapped_column(UInt, default=0, server_default="0")


class Post(Base):
    __tablename__ = "posts"
    __table_args__ = (Index("idx_posts_account_time", "ig_account_id", "posted_at"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    ig_account_id: Mapped[int] = mapped_column(BigIntFK, ForeignKey("ig_accounts.id", ondelete="CASCADE"))
    ig_media_id: Mapped[str] = mapped_column(String(64), unique=True)
    type: Mapped[str] = mapped_column(Enum(*POST_TYPES, name="post_type"))
    caption: Mapped[str | None] = mapped_column(Text)
    permalink: Mapped[str | None] = mapped_column(String(1024))
    thumbnail_url: Mapped[str | None] = mapped_column(String(1024))
    posted_at: Mapped[datetime] = mapped_column(DateTime)

    ig_account: Mapped[IgAccount] = relationship(back_populates="posts")
    stats: Mapped[list[PostStats]] = relationship(
        back_populates="post",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="PostStats.captured_at",
    )


class PostStats(Base):
    """Snapshots of a post's metrics over time (stories must be captured within 24h)."""

    __tablename__ = "post_stats"
    __table_args__ = (Index("idx_post_stats", "post_id", "captured_at"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(BigIntFK, ForeignKey("posts.id", ondelete="CASCADE"))
    captured_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    views: Mapped[int] = mapped_column(UInt, default=0, server_default="0")
    reach: Mapped[int] = mapped_column(UInt, default=0, server_default="0")
    likes: Mapped[int] = mapped_column(UInt, default=0, server_default="0")
    comments: Mapped[int] = mapped_column(UInt, default=0, server_default="0")
    saves: Mapped[int] = mapped_column(UInt, default=0, server_default="0")
    shares: Mapped[int] = mapped_column(UInt, default=0, server_default="0")
    reposts: Mapped[int] = mapped_column(UInt, default=0, server_default="0")
    follows: Mapped[int] = mapped_column(UInt, default=0, server_default="0")

    post: Mapped[Post] = relationship(back_populates="stats")


class AudienceStats(Base):
    """Audience breakdown: age ('25-34'), gender ('F'/'M'), city ('Yerevan'), country."""

    __tablename__ = "audience_stats"
    __table_args__ = (
        UniqueConstraint("ig_account_id", "day", "breakdown", "label", name="uq_audience"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    ig_account_id: Mapped[int] = mapped_column(BigIntFK, ForeignKey("ig_accounts.id", ondelete="CASCADE"))
    day: Mapped[date] = mapped_column(Date)
    breakdown: Mapped[str] = mapped_column(Enum(*AUDIENCE_BREAKDOWNS, name="audience_breakdown"))
    label: Mapped[str] = mapped_column(String(100))
    value: Mapped[int] = mapped_column(UInt)

    ig_account: Mapped[IgAccount] = relationship(back_populates="audience_stats")


class AudienceOnlineHours(Base):
    """Heatmap "when is the audience online": weekday (0=Mon … 6=Sun) x hour (0-23)."""

    __tablename__ = "audience_online_hours"
    __table_args__ = (
        UniqueConstraint("ig_account_id", "day", "hour", name="uq_online_hour"),
        CheckConstraint("day <= 6", name="ck_online_day"),
        CheckConstraint("hour <= 23", name="ck_online_hour"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    ig_account_id: Mapped[int] = mapped_column(BigIntFK, ForeignKey("ig_accounts.id", ondelete="CASCADE"))
    day: Mapped[int] = mapped_column(TinyUInt)
    hour: Mapped[int] = mapped_column(TinyUInt)
    value: Mapped[int] = mapped_column(UInt, default=0, server_default="0")
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    ig_account: Mapped[IgAccount] = relationship(back_populates="online_hours")

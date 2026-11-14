"""Competitor tables (block 5 of db/schema.sql) — public data from Instagram Business Discovery only."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.types import BigIntFK, BigIntPK, UInt
from core.database import Base

COMPETITOR_POST_TYPES = ("post", "carousel", "reels")


class Competitor(Base):
    __tablename__ = "competitors"
    __table_args__ = (UniqueConstraint("user_id", "username", name="uq_competitor"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigIntFK, ForeignKey("users.id", ondelete="CASCADE"))
    username: Mapped[str] = mapped_column(String(64))
    ig_user_id: Mapped[str | None] = mapped_column(String(64))
    name: Mapped[str | None] = mapped_column(String(120))
    biography: Mapped[str | None] = mapped_column(Text)
    website: Mapped[str | None] = mapped_column(String(255))
    profile_picture_url: Mapped[str | None] = mapped_column(String(1024))
    added_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime)
    sync_error: Mapped[str | None] = mapped_column(String(255))

    daily_stats: Mapped[list[CompetitorDailyStats]] = relationship(
        back_populates="competitor", cascade="all, delete-orphan", passive_deletes=True
    )
    posts: Mapped[list[CompetitorPost]] = relationship(
        back_populates="competitor", cascade="all, delete-orphan", passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"<Competitor id={self.id} @{self.username}>"


class CompetitorDailyStats(Base):
    """One public snapshot per competitor per day (Business Discovery has no history)."""

    __tablename__ = "competitor_daily_stats"
    __table_args__ = (UniqueConstraint("competitor_id", "day", name="uq_comp_day"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    competitor_id: Mapped[int] = mapped_column(BigIntFK, ForeignKey("competitors.id", ondelete="CASCADE"))
    day: Mapped[date] = mapped_column(Date)
    followers: Mapped[int] = mapped_column(UInt)
    follows_count: Mapped[int | None] = mapped_column(UInt)
    media_count: Mapped[int] = mapped_column(UInt)

    competitor: Mapped[Competitor] = relationship(back_populates="daily_stats")


class CompetitorPost(Base):
    __tablename__ = "competitor_posts"
    __table_args__ = (
        UniqueConstraint("competitor_id", "ig_media_id", name="uq_comp_media"),
        Index("idx_comp_posts", "competitor_id", "posted_at"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    competitor_id: Mapped[int] = mapped_column(BigIntFK, ForeignKey("competitors.id", ondelete="CASCADE"))
    ig_media_id: Mapped[str] = mapped_column(String(64))
    type: Mapped[str] = mapped_column(Enum(*COMPETITOR_POST_TYPES, name="competitor_post_type"))
    caption: Mapped[str | None] = mapped_column(Text)
    permalink: Mapped[str | None] = mapped_column(String(1024))
    media_url: Mapped[str | None] = mapped_column(String(1024))
    thumbnail_url: Mapped[str | None] = mapped_column(String(1024))
    likes: Mapped[int | None] = mapped_column(UInt)  # None: the owner hides like counts
    comments: Mapped[int] = mapped_column(UInt, default=0, server_default="0")
    views: Mapped[int | None] = mapped_column(UInt)
    posted_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    competitor: Mapped[Competitor] = relationship(back_populates="posts")

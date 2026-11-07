from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.types import BigIntFK, BigIntPK, UInt
from core.database import Base
from core.security import decrypt, encrypt

if TYPE_CHECKING:
    from app.models.analytics import (
        AccountDailyStats,
        AudienceOnlineHours,
        AudienceStats,
        Post,
    )
    from app.models.user import User


class IgAccount(Base):
    __tablename__ = "ig_accounts"
    __table_args__ = (Index("idx_ig_user", "user_id"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigIntFK, ForeignKey("users.id", ondelete="CASCADE"))
    ig_user_id: Mapped[str] = mapped_column(String(64), unique=True)
    username: Mapped[str] = mapped_column(String(64))
    profile_pic_url: Mapped[str | None] = mapped_column(String(1024))
    # Always encrypted (Fernet). Use set_access_token() / get_access_token().
    access_token: Mapped[str] = mapped_column(Text)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    followers_count: Mapped[int] = mapped_column(UInt, default=0, server_default="0")
    media_count: Mapped[int] = mapped_column(UInt, default=0, server_default="0")
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime)
    connected_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[User] = relationship(back_populates="ig_accounts")
    daily_stats: Mapped[list[AccountDailyStats]] = relationship(
        back_populates="ig_account", cascade="all, delete-orphan", passive_deletes=True
    )
    posts: Mapped[list[Post]] = relationship(
        back_populates="ig_account", cascade="all, delete-orphan", passive_deletes=True
    )
    audience_stats: Mapped[list[AudienceStats]] = relationship(
        back_populates="ig_account", cascade="all, delete-orphan", passive_deletes=True
    )
    online_hours: Mapped[list[AudienceOnlineHours]] = relationship(
        back_populates="ig_account", cascade="all, delete-orphan", passive_deletes=True
    )

    def set_access_token(self, plain: str) -> None:
        self.access_token = encrypt(plain)

    def get_access_token(self) -> str:
        return decrypt(self.access_token)

    def __repr__(self) -> str:
        return f"<IgAccount id={self.id} @{self.username}>"

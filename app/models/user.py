from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.types import BigIntPK
from core.database import Base

if TYPE_CHECKING:
    from app.models.ig_account import IgAccount

USER_PLANS = ("free", "pro", "business")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(120))
    plan: Mapped[str] = mapped_column(Enum(*USER_PLANS, name="user_plan"), default="free", server_default="free")
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Yerevan", server_default="Asia/Yerevan")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    ig_accounts: Mapped[list[IgAccount]] = relationship(back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"

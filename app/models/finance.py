"""Finance tables (block 4 of db/schema.sql). All money columns are DECIMAL(14,2)."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CHAR, Date, DateTime, Enum, ForeignKey, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.types import BigIntFK, BigIntPK
from core.database import Base

TX_TYPES = ("income", "expense")
TX_STATUSES = ("paid", "pending")
TX_SOURCES = ("manual", "csv", "receipt_scan")
DEAL_STAGES = ("negotiation", "contract", "in_progress", "paid", "lost")

Money = Numeric(14, 2)


class Category(Base):
    """user_id NULL = default category shared by everyone (inserted by db/schema.sql)."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(BigIntFK, ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(80))
    type: Mapped[str] = mapped_column(Enum(*TX_TYPES, name="category_type"))


class Deal(Base):
    """Collaboration with a brand; `stage` drives the kanban columns."""

    __tablename__ = "deals"
    __table_args__ = (Index("idx_deals_stage", "user_id", "stage"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigIntFK, ForeignKey("users.id", ondelete="CASCADE"))
    # FK to contacts.id exists in MySQL; the Contact model comes with the inbox page.
    contact_id: Mapped[int | None] = mapped_column(BigIntFK)
    brand_name: Mapped[str] = mapped_column(String(120))
    deliverables: Mapped[str | None] = mapped_column(String(255))
    amount: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"), server_default="0")
    currency: Mapped[str] = mapped_column(CHAR(3), default="AMD", server_default="AMD")
    stage: Mapped[str] = mapped_column(
        Enum(*DEAL_STAGES, name="deal_stage"), default="negotiation", server_default="negotiation"
    )
    due_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Deleting a deal keeps its transactions (deal_id → NULL), same as the MySQL FK.
    transactions: Mapped[list[Transaction]] = relationship(back_populates="deal")


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (Index("idx_tx_user_date", "user_id", "occurred_at"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigIntFK, ForeignKey("users.id", ondelete="CASCADE"))
    deal_id: Mapped[int | None] = mapped_column(BigIntFK, ForeignKey("deals.id", ondelete="SET NULL"))
    category_id: Mapped[int | None] = mapped_column(BigIntFK, ForeignKey("categories.id", ondelete="SET NULL"))
    type: Mapped[str] = mapped_column(Enum(*TX_TYPES, name="tx_type"))
    amount: Mapped[Decimal] = mapped_column(Money)
    currency: Mapped[str] = mapped_column(CHAR(3), default="AMD", server_default="AMD")
    description: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(Enum(*TX_STATUSES, name="tx_status"), default="paid", server_default="paid")
    source: Mapped[str] = mapped_column(Enum(*TX_SOURCES, name="tx_source"), default="manual", server_default="manual")
    receipt_url: Mapped[str | None] = mapped_column(String(1024))
    occurred_at: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    deal: Mapped[Deal | None] = relationship(back_populates="transactions")
    category: Mapped[Category | None] = relationship()

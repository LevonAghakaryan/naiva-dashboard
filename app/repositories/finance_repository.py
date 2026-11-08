"""DB queries for the finance page. Only SQL here — no percentages, labels or formatting.

Every query is scoped to one user. Date ranges are inclusive: start <= occurred_at <= end.
Only status='paid' transactions count as income/expense; 'pending' is money still expected.
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from sqlalchemy import extract, func, or_, select, update
from sqlalchemy.orm import Session, joinedload

from app.models import Category, Deal, Transaction


class FinanceRepository:
    def __init__(self, db: Session):
        self.db = db

    # ---------- totals ----------

    def sum_paid(self, user_id: int, type_: str, start: date, end: date) -> Decimal:
        return self.db.scalar(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.user_id == user_id,
                Transaction.type == type_,
                Transaction.status == "paid",
                Transaction.occurred_at.between(start, end),
            )
        ) or Decimal("0")

    def monthly_paid(self, user_id: int, start: date, end: date) -> list[tuple[int, int, str, Decimal]]:
        """(year, month, type, sum) for paid transactions in the range."""
        year = extract("year", Transaction.occurred_at)
        month = extract("month", Transaction.occurred_at)
        rows = self.db.execute(
            select(year, month, Transaction.type, func.sum(Transaction.amount))
            .where(
                Transaction.user_id == user_id,
                Transaction.status == "paid",
                Transaction.occurred_at.between(start, end),
            )
            .group_by(year, month, Transaction.type)
        ).all()
        return [(int(r[0]), int(r[1]), r[2], r[3] or Decimal("0")) for r in rows]

    def sum_by_category(self, user_id: int, type_: str, start: date, end: date) -> list[tuple[int | None, str | None, Decimal]]:
        """(category_id, category name, sum) of paid income or expense; category may be None."""
        rows = self.db.execute(
            select(Transaction.category_id, Category.name, func.sum(Transaction.amount))
            .outerjoin(Category, Category.id == Transaction.category_id)
            .where(
                Transaction.user_id == user_id,
                Transaction.type == type_,
                Transaction.status == "paid",
                Transaction.occurred_at.between(start, end),
            )
            .group_by(Transaction.category_id, Category.name)
        ).all()
        return [(r[0], r[1], r[2] or Decimal("0")) for r in rows]

    def pending_income(self, user_id: int) -> list[Transaction]:
        """Pending income not tied to a deal (deals are counted by stage instead)."""
        return list(self.db.scalars(
            select(Transaction).where(
                Transaction.user_id == user_id,
                Transaction.type == "income",
                Transaction.status == "pending",
                Transaction.deal_id.is_(None),
            )
        ))

    # ---------- categories ----------

    def list_categories(self, user_id: int) -> list[Category]:
        return list(self.db.scalars(
            select(Category)
            .where(or_(Category.user_id.is_(None), Category.user_id == user_id))
            .order_by(Category.type, Category.id)
        ))

    def get_category(self, user_id: int, category_id: int) -> Category | None:
        return self.db.scalar(
            select(Category).where(
                Category.id == category_id,
                or_(Category.user_id.is_(None), Category.user_id == user_id),
            )
        )

    def find_category(self, user_id: int, name: str, type_: str) -> Category | None:
        return self.db.scalar(
            select(Category)
            .where(
                Category.name == name,
                Category.type == type_,
                or_(Category.user_id.is_(None), Category.user_id == user_id),
            )
            .order_by(Category.user_id.is_(None))  # user's own category wins
            .limit(1)
        )

    def get_own_category(self, user_id: int, category_id: int) -> Category | None:
        """Only the user's own category (default ones can't be changed)."""
        return self.db.scalar(select(Category).where(Category.id == category_id, Category.user_id == user_id))

    def category_name_exists(self, user_id: int, name: str, type_: str) -> bool:
        return self.db.scalar(
            select(func.count(Category.id)).where(
                func.lower(Category.name) == name.lower(),
                Category.type == type_,
                or_(Category.user_id.is_(None), Category.user_id == user_id),
            )
        ) > 0

    def uncategorize(self, user_id: int, category_id: int) -> None:
        """Same as the MySQL FK ON DELETE SET NULL, done explicitly so every engine behaves alike."""
        self.db.execute(
            update(Transaction)
            .where(Transaction.user_id == user_id, Transaction.category_id == category_id)
            .values(category_id=None)
        )

    # ---------- deals ----------

    def list_deals(self, user_id: int, stages: Sequence[str] | None = None) -> list[Deal]:
        stmt = select(Deal).where(Deal.user_id == user_id)
        if stages:
            stmt = stmt.where(Deal.stage.in_(stages))
        return list(self.db.scalars(stmt.order_by(Deal.due_date.is_(None), Deal.due_date, Deal.id.desc())))

    def get_deal(self, user_id: int, deal_id: int) -> Deal | None:
        return self.db.scalar(select(Deal).where(Deal.id == deal_id, Deal.user_id == user_id))

    # ---------- transactions ----------

    @staticmethod
    def _tx_filters(stmt, user_id: int, end: date | None, type_: str | None, category_id: int | None):
        stmt = stmt.where(Transaction.user_id == user_id)
        if end is not None:
            stmt = stmt.where(Transaction.occurred_at <= end)
        if type_ is not None:
            stmt = stmt.where(Transaction.type == type_)
        if category_id is not None:
            stmt = stmt.where(Transaction.category_id == category_id)
        return stmt

    def count_transactions(self, user_id: int, end: date | None = None,
                           type_: str | None = None, category_id: int | None = None) -> int:
        stmt = self._tx_filters(select(func.count(Transaction.id)), user_id, end, type_, category_id)
        return self.db.scalar(stmt) or 0

    def list_transactions(self, user_id: int, end: date | None = None, limit: int = 10, offset: int = 0,
                          type_: str | None = None, category_id: int | None = None) -> list[Transaction]:
        stmt = self._tx_filters(
            select(Transaction).options(joinedload(Transaction.category)), user_id, end, type_, category_id
        )
        stmt = stmt.order_by(Transaction.occurred_at.desc(), Transaction.id.desc()).limit(limit).offset(offset)
        return list(self.db.scalars(stmt))

    def get_transaction(self, user_id: int, tx_id: int) -> Transaction | None:
        return self.db.scalar(
            select(Transaction)
            .options(joinedload(Transaction.category))
            .where(Transaction.id == tx_id, Transaction.user_id == user_id)
        )

    # ---------- writes ----------

    def add(self, obj: Category | Deal | Transaction) -> None:
        self.db.add(obj)
        self.db.flush()

    def delete(self, obj: Category | Deal | Transaction) -> None:
        self.db.delete(obj)
        self.db.flush()

    def commit(self) -> None:
        self.db.commit()

    def refresh(self, obj: Deal | Transaction) -> None:
        """Reload columns and relationships (e.g. tx.category after category_id changed)."""
        self.db.refresh(obj)

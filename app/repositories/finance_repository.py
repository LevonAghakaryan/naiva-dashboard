"""DB queries for the finance page. Only SQL here — no percentages, labels or formatting.

Every query is scoped to one user. Date ranges are inclusive: start <= occurred_at <= end.
Status in the DB is 'paid' (done) or 'pending'.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import extract, func, select, update
from sqlalchemy.orm import Session, joinedload

from app.models import Category, Transaction


class FinanceRepository:
    def __init__(self, db: Session):
        self.db = db

    # ---------- transactions ----------

    def month_transactions(self, user_id: int, start: date, end: date) -> list[Transaction]:
        """All transactions (done + pending) in the range, newest first."""
        return list(self.db.scalars(
            select(Transaction)
            .options(joinedload(Transaction.category))
            .where(Transaction.user_id == user_id, Transaction.occurred_at.between(start, end))
            .order_by(Transaction.occurred_at.desc(), Transaction.created_at.desc(), Transaction.id.desc())
        ))

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
        """(year, month, type, sum) for done transactions in the range."""
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

    def get_transaction(self, user_id: int, tx_id: int) -> Transaction | None:
        return self.db.scalar(
            select(Transaction)
            .options(joinedload(Transaction.category))
            .where(Transaction.id == tx_id, Transaction.user_id == user_id)
        )

    # ---------- categories ----------

    def own_categories(self, user_id: int) -> list[Category]:
        return list(self.db.scalars(
            select(Category).where(Category.user_id == user_id).order_by(Category.id)
        ))

    def shared_categories(self) -> list[Category]:
        """Old default categories (user_id NULL) from db/schema.sql."""
        return list(self.db.scalars(select(Category).where(Category.user_id.is_(None))))

    def get_own_category(self, user_id: int, category_id: int) -> Category | None:
        return self.db.scalar(select(Category).where(Category.id == category_id, Category.user_id == user_id))

    def move_category(self, user_id: int, from_ids: list[int | None], type_: str, to_id: int) -> None:
        """Re-point the user's transactions of one type from some categories (None = no category) to another."""
        ids = [i for i in from_ids if i is not None]
        cond = Transaction.category_id.in_(ids) if ids else None
        if None in from_ids:
            cond = Transaction.category_id.is_(None) if cond is None else (cond | Transaction.category_id.is_(None))
        if cond is None:
            return
        self.db.execute(
            update(Transaction)
            .where(Transaction.user_id == user_id, Transaction.type == type_, cond)
            .values(category_id=to_id)
            .execution_options(synchronize_session=False)
        )

    # ---------- writes ----------

    def add(self, obj: Category | Transaction) -> None:
        self.db.add(obj)
        self.db.flush()

    def delete(self, obj: Category | Transaction) -> None:
        self.db.delete(obj)
        self.db.flush()

    def commit(self) -> None:
        self.db.commit()

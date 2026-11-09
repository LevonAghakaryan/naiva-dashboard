"""Demo finance data for the demo user (finance-spec.md §12). Used by scripts/seed.py.

Current month: income ֏707,600, expense ֏289,000, net ֏418,600 (41% spent),
4 pending → forecast ֏788,800. Previous 5 months for the charts.
Done transactions of the current month are clamped to days 1..today, so totals are exact on any day.

Only the finance part:  .venv\\Scripts\\python.exe scripts\\seed.py --finance
"""
from __future__ import annotations

import random
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import Category, Deal, Transaction, User
from app.services.finance_service import DEFAULT_CATEGORIES, add_months, month_end

# Previous 5 months (oldest → newest): done income / expense.
HISTORY = [(640_000, 180_000), (720_000, 210_000), (810_000, 190_000), (930_000, 260_000), (1_050_000, 290_000)]
INCOME_SHARES = [("Համագործակցություն", 0.62), ("Գովազդ", 0.21), ("Affiliate", 0.11), ("Այլ եկամուտ", 0.06)]
EXPENSE_SHARES = [("Աշխատավարձ", 0.45), ("Տեխնիկա", 0.25), ("Ծրագրեր", 0.08), ("Տրանսպորտ", 0.12), ("Այլ ծախս", 0.10)]
HISTORY_NAMES = {
    "Համագործակցություն": ["Yerevan Mall · Reels", "Gold Coffee · stories", "Tufenkian Trekking · Reels",
                            "Sunny Hostel · 3 stories", "Dilijan Resort · Carousel"],
    "Գովազդ": ["Lumen Cosmetics · stories", "Kino Park · stories", "Pizza Sole · stories"],
    "Affiliate": ["Booking affiliate", "Travel gear affiliate"],
    "Այլ եկամուտ": ["Վարպետաց դաս (workshop)", "Լուսանկարների վաճառք"],
    "Աշխատավարձ": ["Մոնտաժող"],
    "Տեխնիկա": ["Միկրոֆոն", "Լույս, շտատիվ"],
    "Ծրագրեր": ["CapCut Pro, Canva"],
    "Տրանսպորտ": ["Տաքսի, նկարահանման օր", "Բենզին"],
    "Այլ ծախս": ["Այլ ծախսեր"],
}

# Current month: (day, title, category, signed amount, status)
CURRENT_MONTH = [
    (7, "Tour Armenia · կանխավճար", "Համագործակցություն", 225_000, "paid"),
    (7, "Տաքսի, նկարահանման օր", "Տրանսպորտ", -8_600, "paid"),
    (6, "CapCut Pro, Canva", "Ծրագրեր", -12_400, "paid"),
    (5, "Nova Telecom · Carousel + stories", "Համագործակցություն", 350_000, "paid"),
    (4, "Տեսախցիկի ոսպնյակ", "Տեխնիկա", -148_000, "paid"),
    (3, "Booking affiliate", "Affiliate", 42_600, "paid"),
    (2, "Lumen Cosmetics · stories", "Գովազդ", 90_000, "paid"),
    (1, "Մոնտաժող (հոկտեմբեր)", "Աշխատավարձ", -120_000, "paid"),
    (12, "Grqaser Books · Reels", "Համագործակցություն", 200_000, "pending"),
    (20, "City Mall · կանխավճար", "Համագործակցություն", 300_000, "pending"),
    (15, "Adobe Premiere բաժանորդագրություն", "Ծրագրեր", -9_800, "pending"),
    (30, "Մոնտաժող (նոյեմբեր)", "Աշխատավարձ", -120_000, "pending"),
]


def has_finance(db: Session, user_id: int) -> bool:
    return bool(db.scalar(select(func.count(Transaction.id)).where(Transaction.user_id == user_id)))


def delete_finance(db: Session, user_id: int) -> None:
    db.execute(delete(Transaction).where(Transaction.user_id == user_id))
    db.execute(delete(Deal).where(Deal.user_id == user_id))
    db.execute(delete(Category).where(Category.user_id == user_id))
    db.flush()


def _split(total: int, shares: list[float], step: int = 100) -> list[int]:
    """Split total into parts by shares, rounded to `step`; the last part takes the remainder."""
    parts = [round(total * s / step) * step for s in shares[:-1]]
    return parts + [total - sum(parts)]


def seed_finance(db: Session, user: User, today: date | None = None, rng_seed: int = 7) -> None:
    rng = random.Random(rng_seed)
    today = today or date.today()
    month_start = today.replace(day=1)
    last_day = month_end(month_start).day

    cats: dict[str, Category] = {}
    for name, type_ in DEFAULT_CATEGORIES:
        cats[name] = Category(user_id=user.id, name=name, type=type_)
        db.add(cats[name])
    db.flush()

    def tx(day: date, title: str, cat: str, amount: int, status: str = "paid") -> Transaction:
        return Transaction(
            user_id=user.id, category_id=cats[cat].id, type="income" if amount > 0 else "expense",
            amount=Decimal(abs(amount)), description=title, status=status, source="manual", occurred_at=day,
        )

    for i, (income, expense) in enumerate(HISTORY):
        first = add_months(month_start, i - len(HISTORY))
        days = month_end(first).day
        for shares, total, sign in ((INCOME_SHARES, income, 1), (EXPENSE_SHARES, expense, -1)):
            for (cat, _), amount in zip(shares, _split(total, [s for _, s in shares])):
                pieces = 3 if cat == "Համագործակցություն" else 2 if cat in ("Գովազդ", "Աշխատավարձ") else 1
                for part in _split(amount, [1 / pieces] * pieces):
                    day = first + timedelta(days=rng.randrange(days))
                    db.add(tx(day, rng.choice(HISTORY_NAMES[cat]), cat, sign * part))

    for day, title, cat, amount, status in CURRENT_MONTH:
        day = min(day, today.day) if status == "paid" else min(day, last_day)
        db.add(tx(month_start + timedelta(days=day - 1), title, cat, amount, status))
    db.flush()

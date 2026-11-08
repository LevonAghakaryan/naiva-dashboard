"""Demo finance data (deals + transactions) for the demo user. Used by scripts/seed.py.

The current month is calibrated to the design (PROJECT.md §3, Ֆինանսներ):
income ֏1.24M ▲18% (prev ֏1.05M), expense ֏310K (prev ֏290K), net ֏930K (margin 75%),
pending ֏650K across 3 deals, income sources 62% / 21% / 11% / 6%.
Current-month transactions are placed on days 1..today, so totals are exact on any day.
"""
from __future__ import annotations

import random
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import Category, Deal, Transaction, User

DEFAULT_CATEGORIES = [
    ("Համագործակցություն", "income"), ("Գովազդ", "income"), ("Affiliate", "income"), ("Այլ եկամուտ", "income"),
    ("Տեխնիկա", "expense"), ("Աշխատավարձ", "expense"), ("Ծրագրեր", "expense"),
    ("Ճամփորդություն", "expense"), ("Այլ ծախս", "expense"),
]

# Previous 5 months (oldest → newest): total paid income / expense.
HISTORY = [
    (640_000, 180_000),
    (720_000, 205_000),
    (810_000, 195_000),
    (930_000, 250_000),
    (1_050_000, 290_000),
]
SOURCE_SHARES = {"Համագործակցություն": 0.60, "Գովազդ": 0.22, "Affiliate": 0.12, "Այլ եկամուտ": 0.06}

# Current month: (day, description, category, amount, type)
CURRENT_MONTH = [
    (1, "Մոնտաժող (հոկտեմբեր)", "Աշխատավարձ", 120_000, "expense"),
    (1, "Mountain Coffee · 4 stories", "Համագործակցություն", 168_800, "income"),
    (2, "Stories գովազդ · Kino Park", "Գովազդ", 100_000, "income"),
    (2, "Travel gear affiliate", "Affiliate", 93_800, "income"),
    (3, "Booking affiliate", "Affiliate", 42_600, "income"),
    (3, "Yerevan Wine Days · Reels", "Համագործակցություն", 250_000, "income"),
    (4, "Տեսախցիկի ոսպնյակ", "Տեխնիկա", 148_000, "expense"),
    (4, "Stories գովազդ · Pizza Sole", "Գովազդ", 70_400, "income"),
    (5, "Nova Telecom · Carousel + stories", "Համագործակցություն", 350_000, "income"),  # paid deal
    (6, "Ճամփորդություն Դիլիջան", "Ճամփորդություն", 29_600, "expense"),
    (6, "Վարպետաց դաս (workshop)", "Այլ եկամուտ", 74_400, "income"),
    (7, "CapCut Pro, Canva", "Ծրագրեր", 12_400, "expense"),
    (8, "Stories գովազդ · Lumen Cosmetics", "Գովազդ", 90_000, "income"),
]

# (brand, deliverables, amount, stage, due in N days from today or None)
DEALS = [
    ("City Mall", "2 Reels + 3 stories", 600_000, "negotiation", 30),
    ("Café Central", "3 stories", 120_000, "negotiation", None),
    ("Ararat Fitness", "1 Reels + 2 stories", 250_000, "negotiation", 21),
    ("Tour Armenia", "Reels շարք", 300_000, "contract", 17),
    ("Grqaser Books", "1 Reels", 200_000, "in_progress", 4),
    ("Silk Road Hotel", "5 stories", 150_000, "in_progress", 12),
]
PAID_DEAL = ("Nova Telecom", "Carousel + stories", 350_000)

HISTORY_NAMES = {
    "Համագործակցություն": ["Yerevan Mall · Reels", "Gold Coffee · stories", "Tufenkian Trekking · Reels",
                            "Sunny Hostel · 3 stories", "Dilijan Resort · Carousel"],
    "Գովազդ": ["Stories գովազդ · Lumen Cosmetics", "Stories գովազդ · Kino Park", "Stories գովազդ · Pizza Sole"],
    "Affiliate": ["Booking affiliate", "Travel gear affiliate"],
    "Այլ եկամուտ": ["Վարպետաց դաս (workshop)", "Լուսանկարների վաճառք"],
}
HISTORY_EXPENSES = [
    ("Մոնտաժող", "Աշխատավարձ", 0.55),
    ("CapCut Pro, Canva", "Ծրագրեր", 0.06),
    ("Ճամփորդության ծախսեր", "Ճամփորդություն", 0.24),
    ("Այլ ծախսեր", "Այլ ծախս", 0.15),
]


def add_months(first: date, n: int) -> date:
    idx = first.year * 12 + first.month - 1 + n
    return date(idx // 12, idx % 12 + 1, 1)


def ensure_default_categories(db: Session) -> dict[tuple[str, str], int]:
    """Default categories come from db/schema.sql; add any that are missing (e.g. on a fresh SQLite)."""
    existing = {(c.name, c.type): c.id for c in db.scalars(select(Category).where(Category.user_id.is_(None)))}
    for name, type_ in DEFAULT_CATEGORIES:
        if (name, type_) not in existing:
            cat = Category(user_id=None, name=name, type=type_)
            db.add(cat)
            db.flush()
            existing[(name, type_)] = cat.id
    return existing


def has_finance(db: Session, user_id: int) -> bool:
    return bool(
        db.scalar(select(func.count(Transaction.id)).where(Transaction.user_id == user_id))
        or db.scalar(select(func.count(Deal.id)).where(Deal.user_id == user_id))
    )


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
    cats = ensure_default_categories(db)
    month_start = today.replace(day=1)

    def tx(day: date, desc: str, cat: str, amount: int, type_: str, deal: Deal | None = None) -> Transaction:
        return Transaction(
            user_id=user.id, deal=deal, category_id=cats[(cat, type_)], type=type_,
            amount=Decimal(amount), description=desc, status="paid", source="manual", occurred_at=day,
        )

    # ----- previous 5 months -----
    for i, (income, expense) in enumerate(HISTORY):
        first = add_months(month_start, i - len(HISTORY))
        days_in_month = (add_months(first, 1) - first).days
        names = list(SOURCE_SHARES)
        for cat, amount in zip(names, _split(income, [SOURCE_SHARES[n] for n in names])):
            pieces = 3 if cat == "Համագործակցություն" else 2 if cat == "Գովազդ" else 1
            for part in _split(amount, [1 / pieces] * pieces):
                desc = rng.choice(HISTORY_NAMES[cat])
                db.add(tx(first + timedelta(days=rng.randrange(days_in_month)), desc, cat, part, "income"))
        for (desc, cat, _), amount in zip(HISTORY_EXPENSES, _split(expense, [s for *_, s in HISTORY_EXPENSES])):
            db.add(tx(first + timedelta(days=rng.randrange(days_in_month)), desc, cat, amount, "expense"))

    # ----- deals -----
    for brand, deliverables, amount, stage, due_in in DEALS:
        db.add(Deal(
            user_id=user.id, brand_name=brand, deliverables=deliverables, amount=Decimal(amount),
            stage=stage, due_date=today + timedelta(days=due_in) if due_in is not None else None,
        ))
    brand, deliverables, amount = PAID_DEAL
    paid_deal = Deal(user_id=user.id, brand_name=brand, deliverables=deliverables,
                     amount=Decimal(amount), stage="paid", due_date=month_start + timedelta(days=min(4, today.day - 1)))
    db.add(paid_deal)
    db.flush()

    # ----- current month (days clamped to today) -----
    for day, desc, cat, amount, type_ in CURRENT_MONTH:
        occurred = month_start + timedelta(days=min(day, today.day) - 1)
        deal = paid_deal if desc.startswith(PAID_DEAL[0]) else None
        db.add(tx(occurred, desc, cat, amount, type_, deal))
    db.flush()



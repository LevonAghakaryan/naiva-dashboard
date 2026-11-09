"""Request/response shapes for /api/finance/* (the "Ֆինանսներ" page, docs: finance-spec.md).

Money goes out as signed integers in AMD: income > 0, expense < 0. The frontend formats it.
Status in the API is "done" | "pending" (stored in the DB as 'paid' | 'pending').
"""
from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

TxType = Literal["income", "expense"]
TxStatus = Literal["done", "pending"]

MonthStr = Annotated[str, StringConstraints(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")]
Title = Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)]
CategoryName = Annotated[str, StringConstraints(strip_whitespace=True, max_length=80)]


# ---------- pieces of GET /api/finance/page ----------

class SummaryOut(BaseModel):
    income: int  # done income of the month
    expense: int  # done expense of the month (absolute value)
    net: int  # income − expense, may be negative
    net_pct: int | None  # net / income × 100 ("+68% եկամտից"); None without income
    spent_pct: int  # round(expense / income × 100), max 100; 0 without income
    income_count: int
    expense_count: int
    prev_income: int
    prev_expense: int
    forecast: int | None  # net + all pending amounts; None when nothing is pending


class TransactionOut(BaseModel):
    id: int
    date: date
    title: str
    category_id: int | None
    category: str
    amount: int  # signed
    status: TxStatus


class PendingOut(BaseModel):
    income: int  # sum of pending income (> 0)
    expense: int  # sum of pending expense (< 0)
    items: list[TransactionOut]  # by date


class CalendarDay(BaseModel):
    date: date
    income: int
    expense: int  # absolute value
    net: int
    count: int  # done transactions that day
    pending: int  # pending transactions that day


class CategoryOut(BaseModel):
    id: int
    name: str
    type: TxType
    is_system: bool  # "Այլ եկամուտ" / "Այլ ծախս" can't be deleted
    count: int  # done transactions in the selected month


class MonthTotals(BaseModel):
    month: str
    label: str = Field(examples=["Նոյ"])
    income: int
    expense: int


class CategoryShare(BaseModel):
    category_id: int | None
    name: str
    amount: int  # absolute value
    percent: int


class FinancePageOut(BaseModel):
    month: str = Field(examples=["2026-11"])
    month_label: str = Field(examples=["Նոյեմբեր 2026"])
    today: date
    summary: SummaryOut
    transactions: list[TransactionOut]  # done, newest first
    pending: PendingOut
    calendar: list[CalendarDay]  # every day of the month
    categories: list[CategoryOut]  # income first, "Այլ" last within each type
    monthly: list[MonthTotals]  # last 6 months, oldest → newest
    by_category: dict[TxType, list[CategoryShare]]  # biggest first


# ---------- writes ----------

class TransactionIn(BaseModel):
    type: TxType  # decides the sign
    amount: Annotated[int, Field(gt=0, lt=10**12)]
    date: date
    title: Title | None = None  # empty → category name
    category_id: int | None = None  # empty → "Այլ եկամուտ" / "Այլ ծախս"
    status: TxStatus = "done"


class CategoryIn(BaseModel):
    name: CategoryName
    type: TxType

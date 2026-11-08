"""Request/response shapes for /api/finance/* (the "Ֆինանսներ" page).

Money goes out as plain numbers (AMD); the frontend formats it (֏1.24M, ֏1,240,000).
Money comes in as Decimal so nothing is lost before it is stored in DECIMAL(14,2).
"""
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

TxType = Literal["income", "expense"]
TxStatus = Literal["paid", "pending"]
DealStage = Literal["negotiation", "contract", "in_progress", "paid", "lost"]
Direction = Literal["up", "down", "flat"]

MonthStr = Annotated[str, StringConstraints(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")]
Amount = Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=2)]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)]
BrandName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
CategoryName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]


# ---------- GET /api/finance/summary ----------

class MoneyKpi(BaseModel):
    key: str = Field(examples=["income"])
    label: str = Field(examples=["Եկամուտ"])
    value: float
    previous: float  # previous calendar month
    change_pct: float | None
    direction: Direction
    good: bool  # pill color: expenses going up is bad


class PendingKpi(BaseModel):
    label: str = "Սպասվող վճարումներ"
    value: float
    count: int  # deals in contract/in_progress + pending income transactions
    nearest_due: date | None  # "ամենամոտը՝ Նոյ 12"


class FinanceSummaryOut(BaseModel):
    month: str = Field(examples=["2026-11"])
    month_label: str = Field(examples=["Նոյեմբեր 2026"])
    income: MoneyKpi
    expense: MoneyKpi
    net: MoneyKpi
    margin_pct: float | None  # net / income × 100
    pending: PendingKpi


# ---------- GET /api/finance/monthly ----------

class MonthTotals(BaseModel):
    month: str
    label: str = Field(examples=["Նոյ"])
    income: float
    expense: float


class MonthlyOut(BaseModel):
    items: list[MonthTotals]  # oldest → newest, the selected month is last


# ---------- GET /api/finance/sources?type=income|expense ----------

class SourceItem(BaseModel):
    category_id: int | None
    label: str
    amount: float
    percent: float


class SourcesOut(BaseModel):
    month: str
    type: TxType
    total: float
    items: list[SourceItem]  # biggest first


# ---------- categories ----------

class CategoryOut(BaseModel):
    id: int
    name: str
    type: TxType
    own: bool  # created by the user → can be deleted; default ones can't


class CategoryIn(BaseModel):
    name: CategoryName
    type: TxType


# ---------- deals (kanban) ----------

class DealOut(BaseModel):
    id: int
    brand_name: str
    deliverables: str | None
    amount: float
    stage: DealStage
    due_date: date | None


class DealColumn(BaseModel):
    stage: DealStage
    label: str = Field(examples=["Բանակցություն"])
    count: int
    total: float
    items: list[DealOut]


class DealsBoardOut(BaseModel):
    active_count: int  # everything not paid / lost
    active_total: float
    columns: list[DealColumn]  # negotiation → contract → in_progress → paid
    lost: list[DealOut]


class DealIn(BaseModel):
    brand_name: BrandName
    deliverables: ShortText | None = None
    amount: Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2)] = Decimal("0")
    stage: DealStage = "negotiation"
    due_date: date | None = None


class DealPatch(BaseModel):
    brand_name: BrandName | None = None
    deliverables: ShortText | None = None
    amount: Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2)] | None = None
    stage: DealStage | None = None
    due_date: date | None = None


# ---------- transactions ----------

class TransactionOut(BaseModel):
    id: int
    occurred_at: date
    description: str | None
    type: TxType
    category_id: int | None
    category: str | None
    status: TxStatus
    status_label: str = Field(examples=["Վճարված", "Ծախս", "Սպասվող"])
    amount: float
    deal_id: int | None


class TransactionsOut(BaseModel):
    total: int
    items: list[TransactionOut]  # newest first


class TransactionIn(BaseModel):
    type: TxType
    amount: Amount
    occurred_at: date
    description: ShortText | None = None
    category_id: int | None = None
    status: TxStatus = "paid"


class TransactionPatch(BaseModel):
    type: TxType | None = None
    amount: Amount | None = None
    occurred_at: date | None = None
    description: ShortText | None = None
    category_id: int | None = None
    status: TxStatus | None = None

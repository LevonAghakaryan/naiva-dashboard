"""Business logic for the finance page: months, % change, margin, sources, kanban, CRUD rules."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from app.models import Deal, Transaction
from app.repositories.finance_repository import FinanceRepository
from app.schemas.finance import (
    CategoryOut,
    DealColumn,
    DealIn,
    DealOut,
    DealPatch,
    DealsBoardOut,
    FinanceSummaryOut,
    MoneyKpi,
    MonthlyOut,
    MonthTotals,
    PendingKpi,
    SourceItem,
    SourcesOut,
    TransactionIn,
    TransactionOut,
    TransactionPatch,
    TransactionsOut,
)

MONTHS_SHORT = ["Հունվ", "Փետր", "Մարտ", "Ապր", "Մայիս", "Հունիս",
                "Հուլիս", "Օգոստ", "Սեպտ", "Հոկտ", "Նոյ", "Դեկտ"]
MONTHS_FULL = ["Հունվար", "Փետրվար", "Մարտ", "Ապրիլ", "Մայիս", "Հունիս",
               "Հուլիս", "Օգոստոս", "Սեպտեմբեր", "Հոկտեմբեր", "Նոյեմբեր", "Դեկտեմբեր"]

BOARD_STAGES = ["negotiation", "contract", "in_progress", "paid"]
STAGE_LABELS = {
    "negotiation": "Բանակցություն",
    "contract": "Պայմանագիր",
    "in_progress": "Կատարման մեջ",
    "paid": "Վճարված",
    "lost": "Չկայացած",
}
PENDING_STAGES = ["contract", "in_progress"]  # agreed, money not received yet
PAID_COLUMN_LIMIT = 6  # the "Վճարված" column shows only the latest ones
DEAL_CATEGORY = "Համագործակցություն"
UNCATEGORIZED = "Առանց կատեգորիայի"


class FinanceNotFound(LookupError):
    pass


class FinanceInvalid(ValueError):
    pass


# ---------- month helpers ----------

def parse_month(value: str | None, today: date) -> date:
    """'2026-11' → date(2026, 11, 1); None → the current month."""
    if not value:
        return today.replace(day=1)
    year, month = value.split("-")
    return date(int(year), int(month), 1)


def month_end(first: date) -> date:
    return add_months(first, 1) - timedelta(days=1)


def add_months(first: date, n: int) -> date:
    idx = first.year * 12 + first.month - 1 + n
    return date(idx // 12, idx % 12 + 1, 1)


def month_key(first: date) -> str:
    return f"{first.year:04d}-{first.month:02d}"


def pct_change(value: Decimal, previous: Decimal) -> float | None:
    if previous == 0:
        return None
    return round(float((value - previous) / previous * 100), 1)


def _money_kpi(key: str, label: str, value: Decimal, previous: Decimal, higher_is_good: bool = True) -> MoneyKpi:
    direction = "up" if value > previous else "down" if value < previous else "flat"
    good = direction == "flat" or ((direction == "up") == higher_is_good)
    return MoneyKpi(key=key, label=label, value=float(value), previous=float(previous),
                    change_pct=pct_change(value, previous), direction=direction, good=good)


def _deal_out(d: Deal) -> DealOut:
    return DealOut(id=d.id, brand_name=d.brand_name, deliverables=d.deliverables,
                   amount=float(d.amount or 0), stage=d.stage, due_date=d.due_date)


def _status_label(tx: Transaction) -> str:
    if tx.status == "pending":
        return "Սպասվող"
    return "Վճարված" if tx.type == "income" else "Ծախս"


def _tx_out(tx: Transaction) -> TransactionOut:
    return TransactionOut(
        id=tx.id, occurred_at=tx.occurred_at, description=tx.description, type=tx.type,
        category_id=tx.category_id, category=tx.category.name if tx.category else None,
        status=tx.status, status_label=_status_label(tx), amount=float(tx.amount), deal_id=tx.deal_id,
    )


class FinanceService:
    def __init__(self, repo: FinanceRepository, user_id: int, today: date | None = None):
        self.repo = repo
        self.user_id = user_id
        self.today = today or date.today()

    # ---------- KPI ----------

    def summary(self, month: str | None) -> FinanceSummaryOut:
        first = parse_month(month, self.today)
        prev = add_months(first, -1)
        cur_range, prev_range = (first, month_end(first)), (prev, month_end(prev))

        income = self.repo.sum_paid(self.user_id, "income", *cur_range)
        expense = self.repo.sum_paid(self.user_id, "expense", *cur_range)
        p_income = self.repo.sum_paid(self.user_id, "income", *prev_range)
        p_expense = self.repo.sum_paid(self.user_id, "expense", *prev_range)
        net, p_net = income - expense, p_income - p_expense

        return FinanceSummaryOut(
            month=month_key(first),
            month_label=f"{MONTHS_FULL[first.month - 1]} {first.year}",
            income=_money_kpi("income", "Եկամուտ", income, p_income),
            expense=_money_kpi("expense", "Ծախս", expense, p_expense, higher_is_good=False),
            net=_money_kpi("net", "Զուտ շահույթ", net, p_net),
            margin_pct=round(float(net / income * 100), 1) if income > 0 else None,
            pending=self._pending(),
        )

    def _pending(self) -> PendingKpi:
        """Money agreed but not received: contract/in-progress deals + pending income."""
        deals = self.repo.list_deals(self.user_id, PENDING_STAGES)
        txs = self.repo.pending_income(self.user_id)
        total = sum((d.amount or Decimal("0") for d in deals), Decimal("0")) + sum(
            (t.amount for t in txs), Decimal("0"))
        dates = [d.due_date for d in deals if d.due_date] + [t.occurred_at for t in txs]
        upcoming = [d for d in dates if d >= self.today]
        nearest = min(upcoming) if upcoming else (min(dates) if dates else None)
        return PendingKpi(value=float(total), count=len(deals) + len(txs), nearest_due=nearest)

    # ---------- charts ----------

    def monthly(self, month: str | None, months: int) -> MonthlyOut:
        last = parse_month(month, self.today)
        first = add_months(last, -(months - 1))
        sums: dict[tuple[int, int, str], Decimal] = {
            (y, m, t): s for y, m, t, s in self.repo.monthly_paid(self.user_id, first, month_end(last))
        }
        items = []
        for i in range(months):
            m = add_months(first, i)
            items.append(MonthTotals(
                month=month_key(m), label=MONTHS_SHORT[m.month - 1],
                income=float(sums.get((m.year, m.month, "income"), 0)),
                expense=float(sums.get((m.year, m.month, "expense"), 0)),
            ))
        return MonthlyOut(items=items)

    def sources(self, month: str | None) -> SourcesOut:
        first = parse_month(month, self.today)
        rows = self.repo.income_by_category(self.user_id, first, month_end(first))
        total = sum((s for _, _, s in rows), Decimal("0"))
        items = sorted(
            (SourceItem(category_id=cid, label=name or UNCATEGORIZED, amount=float(s),
                        percent=round(float(s / total * 100), 1) if total else 0.0)
             for cid, name, s in rows if s > 0),
            key=lambda i: i.amount, reverse=True,
        )
        return SourcesOut(month=month_key(first), total=float(total), items=items)

    # ---------- categories ----------

    def categories(self) -> list[CategoryOut]:
        return [CategoryOut(id=c.id, name=c.name, type=c.type) for c in self.repo.list_categories(self.user_id)]

    # ---------- deals ----------

    def board(self) -> DealsBoardOut:
        deals = self.repo.list_deals(self.user_id)
        by_stage: dict[str, list[Deal]] = {s: [] for s in STAGE_LABELS}
        for d in deals:
            by_stage[d.stage].append(d)
        # Paid column: most recent first (due date, then newest id).
        by_stage["paid"].sort(key=lambda d: (d.due_date or date.min, d.id), reverse=True)

        columns = []
        for stage in BOARD_STAGES:
            items = by_stage[stage]
            shown = items[:PAID_COLUMN_LIMIT] if stage == "paid" else items
            columns.append(DealColumn(
                stage=stage, label=STAGE_LABELS[stage], count=len(items),
                total=float(sum((d.amount or Decimal("0") for d in items), Decimal("0"))),
                items=[_deal_out(d) for d in shown],
            ))
        active = [d for d in deals if d.stage not in ("paid", "lost")]
        return DealsBoardOut(
            active_count=len(active),
            active_total=float(sum((d.amount or Decimal("0") for d in active), Decimal("0"))),
            columns=columns,
            lost=[_deal_out(d) for d in by_stage["lost"]],
        )

    def create_deal(self, data: DealIn) -> DealOut:
        deal = Deal(user_id=self.user_id, **data.model_dump())
        self.repo.add(deal)
        if deal.stage == "paid":
            self._record_deal_payment(deal)
        self.repo.commit()
        return _deal_out(deal)

    def update_deal(self, deal_id: int, data: DealPatch) -> DealOut:
        deal = self._deal(deal_id)
        changes = data.model_dump(exclude_unset=True)
        if "brand_name" in changes and changes["brand_name"] is None:
            raise FinanceInvalid("Բրենդի անունը պարտադիր է։")
        if "amount" in changes and changes["amount"] is None:
            changes["amount"] = Decimal("0")
        if "stage" in changes and changes["stage"] is None:
            raise FinanceInvalid("Փուլը պարտադիր է։")
        became_paid = changes.get("stage") == "paid" and deal.stage != "paid"
        for key, value in changes.items():
            setattr(deal, key, value)
        if became_paid:
            self._record_deal_payment(deal)
        self.repo.commit()
        return _deal_out(deal)

    def delete_deal(self, deal_id: int) -> None:
        self.repo.delete(self._deal(deal_id))
        self.repo.commit()

    def _deal(self, deal_id: int) -> Deal:
        deal = self.repo.get_deal(self.user_id, deal_id)
        if deal is None:
            raise FinanceNotFound("Համագործակցությունը չի գտնվել։")
        return deal

    def _record_deal_payment(self, deal: Deal) -> None:
        """Moving a deal to "Վճարված" books the income once (pending ones become paid)."""
        linked = list(deal.transactions)
        if linked:
            for tx in linked:
                if tx.type == "income" and tx.status == "pending":
                    tx.status = "paid"
            return
        if not deal.amount or deal.amount <= 0:
            return
        category = self.repo.find_category(self.user_id, DEAL_CATEGORY, "income")
        description = deal.brand_name + (f" · {deal.deliverables}" if deal.deliverables else "")
        self.repo.add(Transaction(
            user_id=self.user_id, deal=deal, category_id=category.id if category else None,
            type="income", amount=deal.amount, currency=deal.currency or "AMD",
            description=description[:255], status="paid", source="manual", occurred_at=self.today,
        ))

    # ---------- transactions ----------

    def transactions(self, month: str | None, limit: int, offset: int) -> TransactionsOut:
        """Newest first, up to the end of the selected month ("load more" pages back in time)."""
        end = month_end(parse_month(month, self.today)) if month else None
        items = self.repo.list_transactions(self.user_id, end, limit, offset)
        return TransactionsOut(
            total=self.repo.count_transactions(self.user_id, end),
            items=[_tx_out(t) for t in items],
        )

    def create_transaction(self, data: TransactionIn) -> TransactionOut:
        self._check_category(data.category_id, data.type)
        tx = Transaction(user_id=self.user_id, source="manual", **data.model_dump())
        self.repo.add(tx)
        self.repo.commit()
        return _tx_out(self._tx(tx.id))

    def update_transaction(self, tx_id: int, data: TransactionPatch) -> TransactionOut:
        tx = self._tx(tx_id)
        changes = data.model_dump(exclude_unset=True)
        for key in ("type", "amount", "occurred_at", "status"):
            if key in changes and changes[key] is None:
                raise FinanceInvalid("Պարտադիր դաշտը դատարկ է։")
        new_type = changes.get("type", tx.type)
        new_category = changes.get("category_id", tx.category_id)
        if "type" in changes or "category_id" in changes:
            self._check_category(new_category, new_type)
        for key, value in changes.items():
            setattr(tx, key, value)
        self.repo.commit()
        self.repo.refresh(tx)
        return _tx_out(tx)

    def delete_transaction(self, tx_id: int) -> None:
        self.repo.delete(self._tx(tx_id))
        self.repo.commit()

    def _tx(self, tx_id: int) -> Transaction:
        tx = self.repo.get_transaction(self.user_id, tx_id)
        if tx is None:
            raise FinanceNotFound("Գործարքը չի գտնվել։")
        return tx

    def _check_category(self, category_id: int | None, type_: str) -> None:
        if category_id is None:
            return
        category = self.repo.get_category(self.user_id, category_id)
        if category is None:
            raise FinanceInvalid("Կատեգորիան չի գտնվել։")
        if category.type != type_:
            kind = "եկամտի" if type_ == "income" else "ծախսի"
            raise FinanceInvalid(f"Ընտրեք {kind} կատեգորիա։")

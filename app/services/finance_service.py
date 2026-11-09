"""Business logic for the finance page (rules: finance-spec.md §3).

- Income / expense / net count only done transactions of the selected calendar month.
- Pending transactions count nowhere until confirmed; they only feed the forecast
  (net + every pending amount of the month) and the calendar's yellow dot.
- Every user has their own categories. "Այլ եկամուտ" / "Այլ ծախս" are system ones and can't be
  deleted; deleting any other category moves its transactions into "Այլ" of the same type.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from app.models import Category, Transaction
from app.repositories.finance_repository import FinanceRepository
from app.schemas.finance import (
    CalendarDay,
    CategoryIn,
    CategoryOut,
    CategoryShare,
    FinancePageOut,
    MonthTotals,
    PendingOut,
    SummaryOut,
    TransactionIn,
    TransactionOut,
)

MONTHS_SHORT = ["Հունվ", "Փետր", "Մարտ", "Ապր", "Մայիս", "Հունիս",
                "Հուլիս", "Օգոստ", "Սեպտ", "Հոկտ", "Նոյ", "Դեկտ"]
MONTHS_FULL = ["Հունվար", "Փետրվար", "Մարտ", "Ապրիլ", "Մայիս", "Հունիս",
               "Հուլիս", "Օգոստոս", "Սեպտեմբեր", "Հոկտեմբեր", "Նոյեմբեր", "Դեկտեմբեր"]

OTHER = {"income": "Այլ եկամուտ", "expense": "Այլ ծախս"}  # system categories
DEFAULT_CATEGORIES = [
    ("Համագործակցություն", "income"), ("Գովազդ", "income"), ("Affiliate", "income"), ("Այլ եկամուտ", "income"),
    ("Տեխնիկա", "expense"), ("Աշխատավարձ", "expense"), ("Ծրագրեր", "expense"), ("Տրանսպորտ", "expense"),
    ("Այլ ծախս", "expense"),
]
RENAMED = {"Ճամփորդություն": "Տրանսպորտ"}  # old shared default → new default
CHART_MONTHS = 6

DB_STATUS = {"done": "paid", "pending": "pending"}
API_STATUS = {v: k for k, v in DB_STATUS.items()}


class FinanceNotFound(LookupError):
    pass


class FinanceInvalid(ValueError):
    pass


# ---------- helpers ----------

def parse_month(value: str | None, today: date) -> date:
    """'2026-11' → date(2026, 11, 1); None → the current month."""
    if not value:
        return today.replace(day=1)
    year, month = value.split("-")
    return date(int(year), int(month), 1)


def add_months(first: date, n: int) -> date:
    idx = first.year * 12 + first.month - 1 + n
    return date(idx // 12, idx % 12 + 1, 1)


def month_end(first: date) -> date:
    return add_months(first, 1) - timedelta(days=1)


def month_key(first: date) -> str:
    return f"{first.year:04d}-{first.month:02d}"


def to_int(value: Decimal | int) -> int:
    return int(Decimal(value).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def pct(part: Decimal | int, whole: Decimal | int) -> int:
    """Half-up rounded percent (Python's round() is banker's rounding)."""
    return to_int(Decimal(part) * 100 / Decimal(whole))


def signed(tx: Transaction) -> int:
    value = to_int(tx.amount)
    return value if tx.type == "income" else -value


def is_system(c: Category) -> bool:
    return OTHER.get(c.type) == c.name


def _category_name(tx: Transaction) -> str:
    return tx.category.name if tx.category else OTHER[tx.type]


def _tx_out(tx: Transaction) -> TransactionOut:
    return TransactionOut(
        id=tx.id, date=tx.occurred_at, title=tx.description or _category_name(tx),
        category_id=tx.category_id, category=_category_name(tx),
        amount=signed(tx), status=API_STATUS[tx.status],
    )


def _sorted_categories(cats: list[Category]) -> list[Category]:
    """Income first; inside a type in creation order, "Այլ" always last."""
    return sorted(cats, key=lambda c: (c.type != "income", is_system(c), c.id))


class FinanceService:
    def __init__(self, repo: FinanceRepository, user_id: int, today: date | None = None):
        self.repo = repo
        self.user_id = user_id
        self.today = today or date.today()

    # ---------- the whole page ----------

    def page(self, month: str | None) -> FinancePageOut:
        cats = self._categories()
        first = parse_month(month, self.today)
        end = month_end(first)
        txs = self.repo.month_transactions(self.user_id, first, end)
        done = [t for t in txs if t.status == "paid"]
        pending = sorted((t for t in txs if t.status == "pending"), key=lambda t: (t.occurred_at, t.id))

        income = sum(signed(t) for t in done if t.type == "income")
        expense = -sum(signed(t) for t in done if t.type == "expense")
        net = income - expense
        prev = add_months(first, -1)
        pending_income = sum(signed(t) for t in pending if t.type == "income")
        pending_expense = sum(signed(t) for t in pending if t.type == "expense")

        summary = SummaryOut(
            income=income, expense=expense, net=net,
            net_pct=pct(net, income) if income > 0 else None,
            spent_pct=min(100, pct(expense, income)) if income > 0 else 0,
            income_count=sum(1 for t in done if t.type == "income"),
            expense_count=sum(1 for t in done if t.type == "expense"),
            prev_income=to_int(self.repo.sum_paid(self.user_id, "income", prev, month_end(prev))),
            prev_expense=to_int(self.repo.sum_paid(self.user_id, "expense", prev, month_end(prev))),
            forecast=net + pending_income + pending_expense if pending else None,
        )

        return FinancePageOut(
            month=month_key(first),
            month_label=f"{MONTHS_FULL[first.month - 1]} {first.year}",
            today=self.today,
            summary=summary,
            transactions=[_tx_out(t) for t in done],
            pending=PendingOut(income=pending_income, expense=pending_expense,
                               items=[_tx_out(t) for t in pending]),
            calendar=self._calendar(first, end, done, pending),
            categories=self._category_counts(cats, done),
            monthly=self._monthly(first),
            by_category={"income": self._shares(done, "income"), "expense": self._shares(done, "expense")},
        )

    @staticmethod
    def _calendar(first: date, end: date, done: list[Transaction], pending: list[Transaction]) -> list[CalendarDay]:
        income: dict[date, int] = defaultdict(int)
        expense: dict[date, int] = defaultdict(int)
        count: dict[date, int] = defaultdict(int)
        waiting: dict[date, int] = defaultdict(int)
        for t in done:
            (income if t.type == "income" else expense)[t.occurred_at] += to_int(t.amount)
            count[t.occurred_at] += 1
        for t in pending:
            waiting[t.occurred_at] += 1
        days = []
        for i in range((end - first).days + 1):
            d = first + timedelta(days=i)
            days.append(CalendarDay(date=d, income=income[d], expense=expense[d], net=income[d] - expense[d],
                                    count=count[d], pending=waiting[d]))
        return days

    @staticmethod
    def _category_counts(cats: list[Category], done: list[Transaction]) -> list[CategoryOut]:
        counts: dict[int | None, int] = defaultdict(int)
        for t in done:
            counts[t.category_id] += 1
        return [CategoryOut(id=c.id, name=c.name, type=c.type, is_system=is_system(c), count=counts[c.id])
                for c in cats]

    @staticmethod
    def _shares(done: list[Transaction], type_: str) -> list[CategoryShare]:
        sums: dict[tuple[int | None, str], int] = defaultdict(int)
        for t in done:
            if t.type == type_:
                sums[(t.category_id, _category_name(t))] += to_int(t.amount)
        total = sum(sums.values())
        items = [CategoryShare(category_id=cid, name=name, amount=amount, percent=pct(amount, total))
                 for (cid, name), amount in sums.items() if amount > 0]
        return sorted(items, key=lambda i: i.amount, reverse=True)

    def _monthly(self, last: date) -> list[MonthTotals]:
        first = add_months(last, -(CHART_MONTHS - 1))
        sums = {(y, m, t): s for y, m, t, s in self.repo.monthly_paid(self.user_id, first, month_end(last))}
        items = []
        for i in range(CHART_MONTHS):
            m = add_months(first, i)
            items.append(MonthTotals(
                month=month_key(m), label=MONTHS_SHORT[m.month - 1],
                income=to_int(sums.get((m.year, m.month, "income"), 0)),
                expense=to_int(sums.get((m.year, m.month, "expense"), 0)),
            ))
        return items

    # ---------- transactions ----------

    def create_transaction(self, data: TransactionIn) -> TransactionOut:
        tx = Transaction(user_id=self.user_id, source="manual")
        self._apply(tx, data)
        self.repo.add(tx)
        self.repo.commit()
        return _tx_out(tx)

    def update_transaction(self, tx_id: int, data: TransactionIn) -> TransactionOut:
        """Edit any field of a done or pending transaction (type, amount, date, title, category, status)."""
        tx = self._tx(tx_id)
        self._apply(tx, data)
        self.repo.commit()
        return _tx_out(tx)

    def _apply(self, tx: Transaction, data: TransactionIn) -> None:
        cats = self._categories()
        if data.category_id is None:
            category = self._other(cats, data.type)
        else:
            category = next((c for c in cats if c.id == data.category_id), None)
            if category is None:
                raise FinanceInvalid("Կատեգորիան չի գտնվել։")
            if category.type != data.type:
                kind = "եկամտի" if data.type == "income" else "ծախսի"
                raise FinanceInvalid(f"Ընտրիր {kind} կատեգորիա։")
        tx.category = category
        tx.type = data.type
        tx.amount = Decimal(data.amount)
        tx.description = (data.title or category.name)[:255]
        tx.status = DB_STATUS[data.status]
        tx.occurred_at = data.date

    def confirm_transaction(self, tx_id: int) -> TransactionOut:
        """«Ստացա» / «Վճարեցի»: pending → done, the date stays."""
        tx = self._tx(tx_id)
        tx.status = "paid"
        self.repo.commit()
        return _tx_out(tx)

    def delete_transaction(self, tx_id: int) -> None:
        self.repo.delete(self._tx(tx_id))
        self.repo.commit()

    def _tx(self, tx_id: int) -> Transaction:
        tx = self.repo.get_transaction(self.user_id, tx_id)
        if tx is None:
            raise FinanceNotFound("Գործարքը չի գտնվել։")
        return tx

    # ---------- categories ----------

    def create_category(self, data: CategoryIn) -> CategoryOut:
        name = " ".join(data.name.split())
        if not name:
            raise FinanceInvalid("Գրիր անունը")
        cats = self._categories()
        if any(c.name.lower() == name.lower() for c in cats):
            raise FinanceInvalid("Այդպիսի կատեգորիա արդեն կա")
        category = Category(user_id=self.user_id, name=name, type=data.type)
        self.repo.add(category)
        self.repo.commit()
        return CategoryOut(id=category.id, name=category.name, type=category.type, is_system=False, count=0)

    def delete_category(self, category_id: int) -> None:
        cats = self._categories()
        category = next((c for c in cats if c.id == category_id), None)
        if category is None:
            raise FinanceNotFound("Կատեգորիան չի գտնվել։")
        if is_system(category):
            raise FinanceInvalid("«Այլ» կատեգորիան չի ջնջվում։")
        self.repo.move_category(self.user_id, [category.id], category.type, self._other(cats, category.type).id)
        self.repo.delete(category)
        self.repo.commit()

    @staticmethod
    def _other(cats: list[Category], type_: str) -> Category:
        return next(c for c in cats if c.type == type_ and is_system(c))

    def _categories(self) -> list[Category]:
        """The user's own categories. On first use the defaults are created for the user and
        transactions still pointing to the old shared defaults (or to no category) are moved over."""
        own = self.repo.own_categories(self.user_id)
        if all(any(c.type == t and c.name == n for c in own) for t, n in OTHER.items()):
            return _sorted_categories(own)

        by_name = {c.name.lower(): c for c in own}
        for name, type_ in DEFAULT_CATEGORIES:
            if name.lower() not in by_name:
                category = Category(user_id=self.user_id, name=name, type=type_)
                self.repo.add(category)
                by_name[name.lower()] = category
        other = {t: by_name[n.lower()] for t, n in OTHER.items()}
        for shared in self.repo.shared_categories():
            target = by_name.get(RENAMED.get(shared.name, shared.name).lower())
            if target is None or target.type != shared.type:
                target = other[shared.type]
            self.repo.move_category(self.user_id, [shared.id], shared.type, target.id)
        for type_, target in other.items():
            self.repo.move_category(self.user_id, [None], type_, target.id)
        self.repo.commit()
        return _sorted_categories(self.repo.own_categories(self.user_id))

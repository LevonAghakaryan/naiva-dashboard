"""The "Գլխավոր" dashboard: a summary built from the analytics, finance and competitor services."""
from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from app.repositories.finance_repository import FinanceRepository
from app.schemas.analytics import Period
from app.schemas.home import FinanceMonth, HomeOut, IncomeKpi, NextPayment, Rival
from app.services.analytics_service import AnalyticsService
from app.services.competitor_service import CompetitorService
from app.services.finance_service import FinanceService, to_int

KPI_KEYS = ("followers", "reach", "er")
TOP_POSTS = 4
PAYMENT_LOOKAHEAD_DAYS = 90


class HomeService:
    def __init__(self, analytics: AnalyticsService, finance: FinanceService,
                 competitors: CompetitorService, finance_repo: FinanceRepository):
        self.analytics = analytics
        self.finance = finance
        self.competitors = competitors
        self.finance_repo = finance_repo
        self.account = analytics.account
        self.today = analytics.today

    def page(self, days: Period) -> HomeOut:
        a = self.analytics.page(days)
        fin = self.finance.page(None)
        comp = self.competitors.page(days)

        posts = sorted(a.posts, key=lambda p: p.views, reverse=True)
        ers = [p.er for p in a.posts if p.reach > 0]

        rivals = [
            Rival(handle=p.handle, is_me=p.is_me, color=p.color,
                  followers=p.metrics.followers, er=p.metrics.er)
            for p in comp.participants if p.is_me or p.has_data
        ]

        return HomeOut(
            days=days, username=self.account.username,
            user_name=self.account.user.name if self.account.user else None,
            period_start=a.period_start, period_end=a.period_end, has_previous=a.has_previous,
            metrics={k: a.metrics[k] for k in KPI_KEYS},
            income=self._income(a.period_start, days),
            finance=FinanceMonth(month_label=fin.month_label, income=fin.summary.income,
                                 expense=fin.summary.expense, pending_income=fin.pending.income),
            next_payment=self._next_payment(),
            best_time=self.analytics.active_hours().best,
            rivals=rivals,
            top_posts=posts[:TOP_POSTS],
            avg_post_er=round(sum(ers) / len(ers), 1) if ers else None,
        )

    def _income(self, start, days: int) -> IncomeKpi:
        user = self.finance.user_id
        end = self.today
        by_day: dict = defaultdict(int)
        for t in self.finance_repo.month_transactions(user, start, end):
            if t.status == "paid" and t.type == "income":
                by_day[t.occurred_at] += to_int(t.amount)
        points = [by_day.get(start + timedelta(days=i), 0) for i in range(days)]
        p_end = start - timedelta(days=1)
        p_start = p_end - timedelta(days=days - 1)
        previous = to_int(self.finance_repo.sum_paid(user, "income", p_start, p_end))
        return IncomeKpi(value=sum(points), previous=previous, points=points)

    def _next_payment(self) -> NextPayment | None:
        user = self.finance.user_id
        txs = self.finance_repo.month_transactions(
            user, self.today - timedelta(days=PAYMENT_LOOKAHEAD_DAYS),
            self.today + timedelta(days=PAYMENT_LOOKAHEAD_DAYS))
        pending = [t for t in txs if t.status == "pending" and t.type == "income"]
        if not pending:
            return None
        # Overdue ones first, then the soonest.
        t = min(pending, key=lambda x: x.occurred_at)
        title = t.description or (t.category.name if t.category else "Վճարում")
        return NextPayment(title=title, amount=abs(to_int(t.amount)), date=t.occurred_at)

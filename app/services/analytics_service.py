"""Business logic for the analytics page (instagram-spec.md): periods, deltas, ER, buckets, heatmap.

Flow metrics (likes, views, …) are summed per day; level metrics (followers, ER,
non-followers reach %) are values at a moment. Reach and accounts engaged are unique
accounts, so their period totals come from account_period_stats when available.
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta

from app.models import AccountDailyStats, AccountPeriodStats, IgAccount, Post, PostStats
from app.repositories.analytics_repository import AnalyticsRepository, AudienceRow
from app.schemas.analytics import (
    ActiveHoursOut,
    AudienceOut,
    BestTime,
    Bucket,
    MetricOut,
    MonthPostsOut,
    PageOut,
    Period,
    PostRow,
    ShareItem,
)

WEEKDAYS = ["Երկ", "Երք", "Չրք", "Հնգ", "Ուրբ", "Շբթ", "Կիր"]

# The Posts list shows feed content only (Reels / Carousel / Post), not stories.
FEED_TYPES = ["reels", "carousel", "post"]

HERO = ["followers", "reach", "er"]
GRID = ["likes", "views", "saves", "shares", "comments", "profile_visits",
        "link_taps", "accounts_engaged", "interactions", "reposts", "follows", "non_followers"]

# key: (label, account_daily_stats column, unique-account metric?)
FLOWS: dict[str, tuple[str, str, bool]] = {
    "new_follows": ("New follows", "new_follows", False),
    "unfollows": ("Unfollows", "unfollows", False),
    "follows": ("Follows", "new_follows", False),
    "reach": ("Reach", "reach", True),
    "views": ("Views", "views", False),
    "accounts_engaged": ("Accounts engaged", "accounts_engaged", True),
    "interactions": ("Interactions", "interactions", False),
    "likes": ("Likes", "likes", False),
    "comments": ("Comments", "comments", False),
    "saves": ("Saves", "saves", False),
    "shares": ("Shares", "shares", False),
    "reposts": ("Reposts", "reposts", False),
    "profile_visits": ("Profile visits", "profile_views", False),
    "link_taps": ("Link taps", "link_taps", False),
}
INVERTED = {"unfollows"}  # growth is bad
WEEKLY_FROM_DAYS = 90  # flows are drawn by week from this period length

GENDER_LABELS = {"F": "Կանայք", "M": "Տղամարդիկ", "U": "Այլ"}
GENDER_ORDER = ["F", "M", "U"]
AGE_ORDER = ["13-17", "18-24", "25-34", "35-44", "45+"]
CITY_LABELS = {
    "Yerevan": "Երևան", "Moscow": "Մոսկվա", "Los Angeles": "Լոս Անջելես",
    "Gyumri": "Գյումրի", "Vanadzor": "Վանաձոր", "Glendale": "Գլենդել",
    "Sochi": "Սոչի", "Krasnodar": "Կրասնոդար", "Paris": "Փարիզ", "Tbilisi": "Թբիլիսի",
    "Abovyan": "Աբովյան", "Kapan": "Կապան", "Hrazdan": "Հրազդան", "Ijevan": "Իջևան",
    "Armavir": "Արմավիր", "Vagharshapat": "Վաղարշապատ",
}
COUNTRY_LABELS = {
    "AM": "Հայաստան", "RU": "Ռուսաստան", "US": "ԱՄՆ", "FR": "Ֆրանսիա", "GE": "Վրաստան",
    "DE": "Գերմանիա", "UA": "Ուկրաինա", "CA": "Կանադա", "IR": "Իրան", "LB": "Լիբանան",
    "AE": "ԱՄԷ", "GB": "Մեծ Բրիտանիա", "AR": "Արգենտինա", "PL": "Լեհաստան", "ES": "Իսպանիա",
}
HEATMAP_SLOTS = [9, 11, 13, 15, 17, 19, 21, 23]  # 2-hour slots: 09–11 … 23–01
BEST_DAY_THRESHOLD = 0.9  # a day is "best" if within 90% of the peak in the best slot
TOP_PLACES = 5


def pct_change(value: float, previous: float) -> float | None:
    if previous == 0:
        return None
    return round((value - previous) / previous * 100, 1) + 0.0  # + 0.0 turns -0.0 into 0.0


def engagement_rate(likes: int, comments: int, saves: int, shares: int, reach: int) -> float:
    if reach <= 0:
        return 0.0
    return round((likes + comments + saves + shares) / reach * 100, 1)


def ratio_pct(part: int, whole: int) -> float:
    return round(part / whole * 100, 2) if whole > 0 else 0.0


def days_label(days: list[int]) -> str:
    """[1, 2, 3] → 'Երք–Հնգ'; [1, 3] → 'Երք, Հնգ'."""
    runs: list[list[int]] = []
    for d in sorted(days):
        if runs and d == runs[-1][-1] + 1:
            runs[-1].append(d)
        else:
            runs.append([d])
    return ", ".join(
        WEEKDAYS[r[0]] if len(r) == 1 else f"{WEEKDAYS[r[0]]}–{WEEKDAYS[r[-1]]}" for r in runs
    )


def week_buckets(start: date, end: date) -> list[Bucket]:
    """7-day buckets ending on `end`; the oldest one is cut at `start` (90 days → 13 buckets)."""
    out: list[Bucket] = []
    e = end
    while e >= start:
        s = max(start, e - timedelta(days=6))
        out.append(Bucket(start=s, end=e))
        e = s - timedelta(days=1)
    return out[::-1]


def bucketize(values: Sequence[float], days: Sequence[date], buckets: Sequence[Bucket]) -> list[float]:
    """Sum daily values into buckets (both sorted oldest → newest)."""
    sums = [0.0] * len(buckets)
    i = 0
    for d, v in zip(days, values):
        while d > buckets[i].end:
            i += 1
        sums[i] += v
    return sums


def post_row(post: Post, st: PostStats | None) -> PostRow:
    m = {k: (getattr(st, k) if st else 0)
         for k in ("views", "reach", "likes", "comments", "saves", "shares", "reposts", "follows")}
    return PostRow(
        id=post.id, caption=post.caption, thumbnail_url=post.thumbnail_url, permalink=post.permalink,
        type=post.type, posted_at=post.posted_at, **m,
        er=engagement_rate(m["likes"], m["comments"], m["saves"], m["shares"], m["reach"]),
    )


def _good(delta: float | None, inverted: bool = False) -> bool | None:
    if delta is None:
        return None
    return delta <= 0 if inverted else delta >= 0


def _shares(counts: dict[str, int], labels: dict[str, str], order: list[str]) -> list[ShareItem]:
    total = sum(counts.values())
    if total == 0:
        return []
    return [
        ShareItem(key=k, label=labels.get(k, k), percent=round(counts.get(k, 0) / total * 100, 1))
        for k in order
    ]


def _top_shares(counts: dict[str, int], labels: dict[str, str]) -> list[ShareItem]:
    """The biggest TOP_PLACES entries, % of the whole breakdown."""
    total = sum(counts.values())
    if total == 0:
        return []
    top = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:TOP_PLACES]
    return [ShareItem(key=k, label=labels.get(k, k), percent=round(v / total * 100, 1)) for k, v in top]


def _age_bucket(label: str) -> str:
    label = label.replace("–", "-").strip()
    return "45+" if label in ("45-54", "55-64", "65+", "45+") else label


DailyRows = dict[date, AccountDailyStats]


def _series(rows: DailyRows, dates: list[date], col: str) -> list[int]:
    return [getattr(rows[d], col) if d in rows else 0 for d in dates]


def _daily_pct(rows: DailyRows, dates: list[date], part_col: str) -> list[float]:
    """part / reach × 100 per day; a day without data repeats the previous value."""
    out: list[float] = []
    last = 0.0
    for d in dates:
        r = rows.get(d)
        if r is not None and r.reach > 0:
            last = ratio_pct(getattr(r, part_col), r.reach)
        out.append(last)
    return out


class AnalyticsService:
    def __init__(self, repo: AnalyticsRepository, account: IgAccount, today: date | None = None):
        self.repo = repo
        self.account = account
        self.today = today or date.today()

    def _periods(self, days: int) -> tuple[date, date, date, date]:
        """Current period ends today; previous period is the same length right before it."""
        end = self.today
        start = end - timedelta(days=days - 1)
        prev_end = start - timedelta(days=1)
        prev_start = prev_end - timedelta(days=days - 1)
        return start, end, prev_start, prev_end

    # ---------- the whole page ----------

    def page(self, days: Period) -> PageOut:
        acc_id = self.account.id
        start, end, p_start, p_end = self._periods(days)
        day_list = [start + timedelta(days=i) for i in range(days)]
        prev_list = [p_start + timedelta(days=i) for i in range(days)]
        cur_rows = {r.day: r for r in self.repo.daily_rows(acc_id, start, end)}
        prev_rows = {r.day: r for r in self.repo.daily_rows(acc_id, p_start, p_end)}
        has_prev = bool(prev_rows)
        weekly = days >= WEEKLY_FROM_DAYS
        weeks = week_buckets(start, end)

        cur_period = self.repo.period_stats(acc_id, end, days)
        prev_period = self.repo.period_stats(acc_id, p_end, days) if has_prev else None

        def total(col: str, unique: bool, daily: list[int], period: AccountPeriodStats | None) -> int:
            # Unique-account metrics: take the API's period value, never sum the days (spec §2).
            if unique and period is not None:
                return int(getattr(period, col))
            return sum(daily)

        metrics: dict[str, MetricOut] = {}
        totals: dict[str, int] = {}
        prev_totals: dict[str, int] = {}
        for key, (label, col, unique) in FLOWS.items():
            daily = _series(cur_rows, day_list, col)
            prev_daily = _series(prev_rows, prev_list, col)
            value = total(col, unique, daily, cur_period)
            previous = total(col, unique, prev_daily, prev_period) if has_prev else None
            totals[key], prev_totals[key] = value, previous or 0
            delta = pct_change(value, previous) if previous is not None else None
            metrics[key] = MetricOut(
                key=key, label=label, kind="flow", unit="count",
                value=value, previous=previous, delta=delta, delta_unit="pct",
                good=_good(delta, key in INVERTED), gran="week" if weekly else "day",
                points=bucketize(daily, day_list, weeks) if weekly else daily,
                prev_points=prev_daily if (has_prev and not weekly) else None,
            )

        metrics["followers"] = self._followers(cur_rows, day_list, totals)
        metrics["er"] = self._engagement_rate(cur_rows, day_list, totals, prev_totals, has_prev)
        metrics["non_followers"] = self._non_followers(cur_rows, day_list, totals["reach"], cur_period)

        posts = [post_row(p, st) for p, st in self.repo.list_posts(acc_id, FEED_TYPES, start, end)]
        return PageOut(
            username=self.account.username, last_synced_at=self.account.last_synced_at,
            days=days, period_start=start, period_end=end, has_previous=has_prev,
            day_buckets=[Bucket(start=d, end=d) for d in day_list], week_buckets=weeks,
            hero=HERO, grid=GRID, metrics=metrics, posts=posts,
        )

    def _followers(self, rows: DailyRows, day_list: list[date], totals: dict[str, int]) -> MetricOut:
        """Level. The delta is the net change of the period: new follows − unfollows."""
        last = self.repo.last_followers_before(self.account.id, day_list[0])
        points: list[float] = []
        for d in day_list:
            if d in rows:
                last = rows[d].followers
            points.append(last or 0)
        value = last if last is not None else self.account.followers_count
        net = totals["new_follows"] - totals["unfollows"] if rows else None
        return MetricOut(
            key="followers", label="Followers", kind="level", unit="count",
            value=value, previous=value - net if net is not None else None,
            delta=net, delta_unit="abs", good=_good(net),
            gran="day", points=points, prev_points=None,
        )

    @staticmethod
    def _engagement_rate(rows: DailyRows, day_list: list[date], totals: dict[str, int],
                         prev_totals: dict[str, int], has_prev: bool) -> MetricOut:
        """Accounts engaged ÷ Reach of the period; the delta is in percentage points."""
        value = ratio_pct(totals["accounts_engaged"], totals["reach"])
        previous = ratio_pct(prev_totals["accounts_engaged"], prev_totals["reach"]) if has_prev else None
        delta = round(value - previous, 1) + 0.0 if previous else None
        return MetricOut(
            key="er", label="Engagement rate", kind="level", unit="pct",
            value=value, previous=previous, delta=delta, delta_unit="pp", good=_good(delta),
            gran="day", points=_daily_pct(rows, day_list, "accounts_engaged"), prev_points=None,
        )

    @staticmethod
    def _non_followers(rows: DailyRows, day_list: list[date], reach_total: int,
                       period: AccountPeriodStats | None) -> MetricOut:
        """Share of the reach that doesn't follow the account. No delta (spec §4.2)."""
        if period is not None:
            nf = period.non_follower_reach
        else:
            nf = sum(rows[d].non_follower_reach for d in day_list if d in rows)
        return MetricOut(
            key="non_followers", label="Non-followers reach", kind="level", unit="pct",
            value=ratio_pct(nf, reach_total), previous=None, delta=None, delta_unit="pct", good=None,
            gran="day", points=_daily_pct(rows, day_list, "non_follower_reach"), prev_points=None,
        )

    # ---------- posts of one month (calendar) ----------

    def month_posts(self, year: int, month: int) -> MonthPostsOut:
        start = date(year, month, 1)
        end = date(year + month // 12, month % 12 + 1, 1) - timedelta(days=1)
        rows = self.repo.list_posts(self.account.id, FEED_TYPES, start, end)
        first = self.repo.first_post_at(self.account.id, FEED_TYPES)
        return MonthPostsOut(
            month=f"{year:04d}-{month:02d}",
            first_month=first.strftime("%Y-%m") if first else None,
            posts=[post_row(p, st) for p, st in rows],
        )

    # ---------- Audience ----------

    def audience(self) -> AudienceOut:
        as_of, rows = self.repo.latest_audience(self.account.id)
        gender: dict[str, int] = {}
        age: dict[str, int] = {}
        city: dict[str, int] = {}
        country: dict[str, int] = {}
        for r in rows:
            self._add_audience_row(r, gender, age, city, country)

        gender_order = [g for g in GENDER_ORDER if g in gender] + [g for g in gender if g not in GENDER_ORDER]
        return AudienceOut(
            as_of=as_of,
            gender=_shares(gender, GENDER_LABELS, gender_order),
            age=_shares(age, {a: a.replace("-", "–") for a in AGE_ORDER}, AGE_ORDER),
            cities=_top_shares(city, CITY_LABELS),
            countries=_top_shares(country, COUNTRY_LABELS),
        )

    @staticmethod
    def _add_audience_row(r: AudienceRow, gender: dict, age: dict, city: dict, country: dict) -> None:
        if r.breakdown == "gender":
            gender[r.label] = gender.get(r.label, 0) + r.value
        elif r.breakdown == "age":
            bucket = _age_bucket(r.label)
            age[bucket] = age.get(bucket, 0) + r.value
        elif r.breakdown == "city":
            name = r.label.split(",")[0].strip()  # Instagram sends "Yerevan, Yerevan"
            city[name] = city.get(name, 0) + r.value
        elif r.breakdown == "country":
            code = r.label.strip().upper()  # ISO code, e.g. "AM"
            country[code] = country.get(code, 0) + r.value

    # ---------- Most active times heatmap ----------

    def active_hours(self) -> ActiveHoursOut:
        hours = {(d, h): v for d, h, v in self.repo.online_hours(self.account.id)}
        grid = [
            [round((hours.get((d, s), 0) + hours.get((d, (s + 1) % 24), 0)) / 2) for s in HEATMAP_SLOTS]
            for d in range(7)
        ]
        max_value = max((max(row) for row in grid), default=0)

        best = None
        if max_value > 0:
            col_totals = [sum(grid[d][i] for d in range(7)) for i in range(len(HEATMAP_SLOTS))]
            slot_idx = max(range(len(HEATMAP_SLOTS)), key=col_totals.__getitem__)
            peak = max(grid[d][slot_idx] for d in range(7))
            best_days = [d for d in range(7) if grid[d][slot_idx] >= BEST_DAY_THRESHOLD * peak]
            start_hour = HEATMAP_SLOTS[slot_idx]
            end_hour = (start_hour + 2) % 24
            best = BestTime(
                days=best_days, days_label=days_label(best_days),
                start_hour=start_hour, end_hour=end_hour,
                hours_label=f"{start_hour:02d}:00–{end_hour:02d}:00",
            )

        return ActiveHoursOut(
            day_labels=WEEKDAYS,
            slot_labels=[f"{s:02d}" for s in HEATMAP_SLOTS],
            grid=grid, max_value=max_value, best=best,
        )

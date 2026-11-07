"""Business logic for the analytics page: periods, % change, ER, labels, heatmap slots."""
from __future__ import annotations

from datetime import date, timedelta

from app.models import IgAccount
from app.repositories.analytics_repository import AnalyticsRepository, AudienceRow
from app.schemas.analytics import (
    ActiveHoursOut,
    AnalyticsType,
    AudienceOut,
    BestTime,
    KpiItem,
    PostRow,
    PostSort,
    PostsOut,
    ReachDailyOut,
    ReachDay,
    ShareItem,
    SummaryOut,
)

MONTHS = ["Հունվ", "Փետր", "Մարտ", "Ապր", "Մայիս", "Հունիս",
          "Հուլիս", "Օգոստ", "Սեպտ", "Հոկտ", "Նոյ", "Դեկտ"]
WEEKDAYS = ["Երկ", "Երք", "Չրք", "Հնգ", "Ուրբ", "Շբթ", "Կիր"]

# Page tab → raw post types (None = everything)
TAB_TYPES: dict[str, list[str] | None] = {
    "all": None,
    "reels": ["reels"],
    "posts": ["post", "carousel"],
    "stories": ["story"],
}
TYPE_LABELS = {"post": "Post", "carousel": "Carousel", "reels": "Reels", "story": "Story"}

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
HEATMAP_SLOTS = [9, 11, 13, 15, 17, 19, 21]  # 2-hour slots: 09–11 … 21–23
BEST_DAY_THRESHOLD = 0.9  # a day is "best" if within 90% of the peak in the best slot
CITIES_TOP = 5


def pct_change(value: int, previous: int) -> float | None:
    if previous == 0:
        return None
    return round((value - previous) / previous * 100, 1)


def engagement_rate(likes: int, comments: int, saves: int, shares: int, reach: int) -> float:
    if reach <= 0:
        return 0.0
    return round((likes + comments + saves + shares) / reach * 100, 1)


def day_label(d: date) -> str:
    return f"{MONTHS[d.month - 1]} {d.day}"


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


def _kpi(key: str, label: str, value: int, previous: int) -> KpiItem:
    direction = "up" if value > previous else "down" if value < previous else "flat"
    return KpiItem(key=key, label=label, value=value, previous=previous,
                   change_pct=pct_change(value, previous), direction=direction)


def _shares(counts: dict[str, int], labels: dict[str, str], order: list[str]) -> list[ShareItem]:
    total = sum(counts.values())
    if total == 0:
        return []
    return [
        ShareItem(key=k, label=labels.get(k, k), percent=round(counts.get(k, 0) / total * 100, 1))
        for k in order
    ]


def _age_bucket(label: str) -> str:
    label = label.replace("–", "-").strip()
    return "45+" if label in ("45-54", "55-64", "65+", "45+") else label


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

    # ---------- KPI ----------

    def summary(self, type_: AnalyticsType, days: int) -> SummaryOut:
        acc_id = self.account.id
        start, end, p_start, p_end = self._periods(days)
        types = TAB_TYPES[type_]

        cur_posts = self.repo.post_totals(acc_id, start, end, types)
        prev_posts = self.repo.post_totals(acc_id, p_start, p_end, types)

        if type_ == "all":
            cur = self.repo.sum_daily_stats(acc_id, start, end)
            prev = self.repo.sum_daily_stats(acc_id, p_start, p_end)
            kpis = [
                _kpi("views", "Views", cur.views, prev.views),
                _kpi("reach", "Reach", cur.reach, prev.reach),
                _kpi("profile_views", "Պրոֆիլի դիտումներ", cur.profile_views, prev.profile_views),
                _kpi("saves", "Saves", cur_posts.saves, prev_posts.saves),
            ]
        else:
            def interactions(t):
                return t.likes + t.comments + t.saves + t.shares

            kpis = [
                _kpi("views", "Views", cur_posts.views, prev_posts.views),
                _kpi("reach", "Reach", cur_posts.reach, prev_posts.reach),
                _kpi("interactions", "Ինտերակցիաներ", interactions(cur_posts), interactions(prev_posts)),
                _kpi("posts_count", "Հրապարակումներ", cur_posts.posts_count, prev_posts.posts_count),
            ]

        return SummaryOut(
            username=self.account.username, type=type_, days=days,
            period_start=start, period_end=end,
            last_synced_at=self.account.last_synced_at, kpis=kpis,
        )

    # ---------- Reach by day ----------

    def reach_daily(self, days: int) -> ReachDailyOut:
        start, end, _, _ = self._periods(days)
        by_day = dict(self.repo.daily_reach(self.account.id, start, end))
        values = [(start + timedelta(days=i)) for i in range(days)]
        reaches = [by_day.get(d, 0) for d in values]
        max_reach = max(reaches, default=0)
        max_idx = reaches.index(max_reach) if max_reach > 0 else -1
        items = [
            ReachDay(day=d, label=day_label(d), reach=r, is_max=(i == max_idx))
            for i, (d, r) in enumerate(zip(values, reaches))
        ]
        return ReachDailyOut(days=days, total=sum(reaches), items=items)

    # ---------- Audience ----------

    def audience(self) -> AudienceOut:
        as_of, rows = self.repo.latest_audience(self.account.id)
        gender: dict[str, int] = {}
        age: dict[str, int] = {}
        city: dict[str, int] = {}
        for r in rows:
            self._add_audience_row(r, gender, age, city)

        city_total = sum(city.values())
        top_cities = sorted(city.items(), key=lambda kv: kv[1], reverse=True)[:CITIES_TOP]
        cities = [
            ShareItem(key=name, label=CITY_LABELS.get(name, name),
                      percent=round(value / city_total * 100, 1))
            for name, value in top_cities
        ] if city_total else []

        gender_order = [g for g in GENDER_ORDER if g in gender] + [g for g in gender if g not in GENDER_ORDER]
        return AudienceOut(
            as_of=as_of,
            gender=_shares(gender, GENDER_LABELS, gender_order),
            age=_shares(age, {a: a.replace("-", "–") for a in AGE_ORDER}, AGE_ORDER),
            cities=cities,
        )

    @staticmethod
    def _add_audience_row(r: AudienceRow, gender: dict, age: dict, city: dict) -> None:
        if r.breakdown == "gender":
            gender[r.label] = gender.get(r.label, 0) + r.value
        elif r.breakdown == "age":
            bucket = _age_bucket(r.label)
            age[bucket] = age.get(bucket, 0) + r.value
        elif r.breakdown == "city":
            name = r.label.split(",")[0].strip()  # Instagram sends "Yerevan, Yerevan"
            city[name] = city.get(name, 0) + r.value

    # ---------- Active hours heatmap ----------

    def active_hours(self) -> ActiveHoursOut:
        hours = {(d, h): v for d, h, v in self.repo.online_hours(self.account.id)}
        grid = [
            [round((hours.get((d, s), 0) + hours.get((d, s + 1), 0)) / 2) for s in HEATMAP_SLOTS]
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
            best = BestTime(
                days=best_days, days_label=days_label(best_days),
                start_hour=start_hour, end_hour=start_hour + 2,
                hours_label=f"{start_hour:02d}:00–{start_hour + 2:02d}:00",
            )

        return ActiveHoursOut(
            day_labels=WEEKDAYS,
            slot_labels=[f"{s:02d}" for s in HEATMAP_SLOTS],
            grid=grid, max_value=max_value, best=best,
        )

    # ---------- Posts table ----------

    def posts(self, type_: AnalyticsType, sort: PostSort, days: int, limit: int) -> PostsOut:
        start, end, _, _ = self._periods(days)
        rows = self.repo.list_posts(self.account.id, TAB_TYPES[type_], start, end)

        items: list[dict] = []
        for post, st in rows:
            m = {k: (getattr(st, k) if st else 0)
                 for k in ("views", "reach", "likes", "comments", "saves", "shares")}
            items.append({
                "id": post.id, "caption": post.caption, "thumbnail_url": post.thumbnail_url,
                "permalink": post.permalink, "type": post.type, "type_label": TYPE_LABELS[post.type],
                "posted_at": post.posted_at, **m,
                "er": engagement_rate(m["likes"], m["comments"], m["saves"], m["shares"], m["reach"]),
            })

        # Green pill = at or above this account's average ER for the period.
        with_reach = [i["er"] for i in items if i["reach"] > 0]
        avg_er = sum(with_reach) / len(with_reach) if with_reach else 0.0
        for i in items:
            i["er_good"] = i["reach"] > 0 and i["er"] >= avg_er

        items.sort(key=lambda i: i[sort], reverse=True)
        return PostsOut(
            type=type_, sort=sort, total=len(items),
            items=[PostRow(**i) for i in items[:limit]],
        )

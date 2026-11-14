"""Business logic for the competitors page.

Only what Instagram Business Discovery returns publicly is compared, and "you" are measured
the same way (followers, posts, likes, comments, views of your posts) so the comparison is fair.
Saves / shares / reach are insights, available only to an account's owner → not used here.

  ER (per post)   = (likes + comments) / followers × 100; the account ER is the average over posts
  Posts per week  = posts in the period / (days / 7)
  Likes, Comments, Views = average per post (hidden likes / missing views are skipped)
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta

from app.integrations import instagram_discovery
from app.integrations.instagram_discovery import DiscoveredAccount, DiscoveryError
from app.models import Competitor, CompetitorDailyStats, CompetitorPost, IgAccount
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.competitor_repository import CompetitorRepository
from app.schemas.competitor import CompetitorPostOut, CompetitorsPageOut, Metrics, Participant
from core.config import settings

MAX_COMPETITORS = 10
ME_COLOR = "#2563EB"
# One color per competitor, by the order they were added (never blue — blue is "you").
COLORS = ["#F59E0B", "#8B5CF6", "#14B8A6", "#EC4899", "#10B981",
          "#0EA5E9", "#F97316", "#6366F1", "#84CC16", "#D946EF"]
FEED_TYPES = ["reels", "carousel", "post"]


class CompetitorNotFound(Exception):
    pass


class CompetitorInvalid(Exception):
    pass


def _avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _metrics(followers: int, rows: list[tuple[int | None, int, int | None]], days: int) -> Metrics:
    """rows: (likes or None, comments, views or None) per post in the period."""
    with_likes = [(lk, c) for lk, c, _ in rows if lk is not None]
    er = _avg([(lk + c) / followers * 100 for lk, c in with_likes]) if followers else 0.0
    return Metrics(
        followers=followers,
        er=round(er, 2),
        posts=round(len(rows) / (days / 7), 2),
        likes=round(_avg([lk for lk, _ in with_likes]), 1),
        comments=round(_avg([c for _, c, _ in rows]), 1),
        views=round(_avg([v for _, _, v in rows if v is not None]), 1),
    )


class CompetitorService:
    def __init__(self, repo: CompetitorRepository, analytics: AnalyticsRepository,
                 account: IgAccount, today: date | None = None):
        self.repo = repo
        self.analytics = analytics
        self.account = account
        self.user_id = account.user_id
        self.today = today or date.today()

    # ---------- page ----------

    def page(self, days: int) -> CompetitorsPageOut:
        end = self.today
        start = end - timedelta(days=days - 1)
        before = start - timedelta(days=1)
        since, until = datetime.combine(start, time.min), datetime.combine(end + timedelta(days=1), time.min)

        participants = [self._me(days, start, end, before)]
        competitors = self.repo.list(self.user_id)
        colors = {c.id: COLORS[i % len(COLORS)] for i, c in enumerate(competitors)}
        posts = self.repo.posts([c.id for c in competitors], since, until)
        by_comp: dict[int, list[CompetitorPost]] = {}
        for p in posts:
            by_comp.setdefault(p.competitor_id, []).append(p)

        followers_of: dict[int, int] = {}
        for c in competitors:
            snap = self.repo.latest_snapshot(c.id, end)
            prev = self.repo.latest_snapshot(c.id, before)
            followers = snap.followers if snap else 0
            followers_of[c.id] = followers
            mine = by_comp.get(c.id, [])
            participants.append(Participant(
                id=c.id, handle=c.username, name=c.name, is_me=False, color=colors[c.id],
                avatar_url=c.profile_picture_url, biography=c.biography, website=c.website,
                follows=snap.follows_count if snap else None, media_count=snap.media_count if snap else None,
                followers_delta=(followers - prev.followers) if snap and prev else None,
                post_count=len(mine), has_data=snap is not None,
                last_synced_at=c.last_synced_at, sync_error=c.sync_error,
                metrics=_metrics(followers, [(p.likes, p.comments, p.views) for p in mine], days),
            ))

        handle_of = {c.id: c.username for c in competitors}
        rows = []
        for p in posts:
            f = followers_of.get(p.competitor_id) or 0
            er = round((p.likes + p.comments) / f * 100, 2) if f and p.likes is not None else None
            rows.append((p, er))
        ers = [er for _, er in rows if er is not None]
        avg_er = round(_avg(ers), 2) if ers else None
        out_posts = [
            CompetitorPostOut(
                id=p.id, competitor_id=p.competitor_id, handle=handle_of[p.competitor_id],
                color=colors[p.competitor_id], type=p.type, caption=p.caption, permalink=p.permalink,
                image_url=p.thumbnail_url or (p.media_url if p.type != "reels" else None),
                posted_at=p.posted_at, likes=p.likes, comments=p.comments, views=p.views,
                er=er, er_good=None if er is None or avg_er is None else er >= avg_er,
            )
            for p, er in rows
        ]
        return CompetitorsPageOut(
            days=days, start=start, end=end, max_competitors=MAX_COMPETITORS,
            sync_enabled=settings.instagram_sync, participants=participants,
            posts=out_posts, avg_post_er=avg_er,
        )

    def _me(self, days: int, start: date, end: date, before: date) -> Participant:
        acc = self.account
        followers = self.repo.my_followers(acc.id, end) or acc.followers_count or 0
        prev = self.repo.my_followers(acc.id, before)
        rows = [
            (st.likes if st else 0, st.comments if st else 0, st.views if st else None)
            for _, st in self.analytics.list_posts(acc.id, FEED_TYPES, start, end)
        ]
        return Participant(
            id=None, handle=acc.username, name=acc.user.name if acc.user else None, is_me=True,
            color=ME_COLOR, avatar_url=acc.profile_pic_url, biography=None, website=None,
            follows=None, media_count=acc.media_count,
            followers_delta=(followers - prev) if prev is not None else None,
            post_count=len(rows), has_data=True, last_synced_at=acc.last_synced_at, sync_error=None,
            metrics=_metrics(followers, rows, days),
        )

    # ---------- add / remove ----------

    def add(self, username: str) -> Competitor:
        if username.lower() == self.account.username.lower():
            raise CompetitorInvalid("Սա քո սեփական հաշիվն է")
        if self.repo.by_username(self.user_id, username):
            raise CompetitorInvalid(f"@{username}-ն արդեն մրցակիցների ցանկում է")
        if self.repo.count(self.user_id) >= MAX_COMPETITORS:
            raise CompetitorInvalid(f"Կարելի է հետևել առավելագույնը {MAX_COMPETITORS} մրցակցի")

        discovered = None
        if settings.instagram_sync:
            try:
                discovered = self._discover(username)
            except DiscoveryError as e:
                raise CompetitorInvalid(str(e)) from e
        comp = self.repo.add(Competitor(user_id=self.user_id, username=username))
        if discovered:
            self._apply(comp, discovered)
        self.repo.commit()
        return comp

    def remove(self, competitor_id: int) -> None:
        comp = self.repo.get(self.user_id, competitor_id)
        if comp is None:
            raise CompetitorNotFound("Մրցակիցը չգտնվեց")
        self.repo.remove(comp)
        self.repo.commit()

    # ---------- sync (Business Discovery) ----------

    def _discover(self, username: str) -> DiscoveredAccount:
        return instagram_discovery.fetch(self.account.ig_user_id, self.account.get_access_token(), username)

    def sync_all(self) -> dict[str, str]:
        """Nightly job: one snapshot per competitor per day + post counters. Returns handle → status."""
        result = {}
        for comp in self.repo.list(self.user_id):
            try:
                self._apply(comp, self._discover(comp.username))
                result[comp.username] = "ok"
            except DiscoveryError as e:
                comp.sync_error = str(e)[:255]
                result[comp.username] = str(e)
        self.repo.commit()
        return result

    def _apply(self, comp: Competitor, d: DiscoveredAccount) -> None:
        comp.ig_user_id = d.ig_user_id
        comp.name = d.name
        comp.biography = d.biography
        comp.website = d.website
        comp.profile_picture_url = d.profile_picture_url
        comp.last_synced_at = datetime.now().replace(microsecond=0)
        comp.sync_error = None

        snap = self.repo.snapshot(comp.id, self.today) if comp.id else None
        if snap is None:
            comp.daily_stats.append(CompetitorDailyStats(
                day=self.today, followers=d.followers, follows_count=d.follows, media_count=d.media_count))
        else:
            snap.followers, snap.follows_count, snap.media_count = d.followers, d.follows, d.media_count

        existing = self.repo.posts_by_media_id(comp.id) if comp.id else {}
        for dp in d.posts:
            post = existing.get(dp.ig_media_id)
            if post is None:
                post = existing[dp.ig_media_id] = CompetitorPost(ig_media_id=dp.ig_media_id, posted_at=dp.posted_at)
                comp.posts.append(post)
            post.type, post.caption, post.permalink = dp.type, dp.caption, dp.permalink
            post.media_url, post.thumbnail_url = dp.media_url, dp.thumbnail_url
            post.likes, post.comments, post.views = dp.likes, dp.comments, dp.views
        self.repo.flush()

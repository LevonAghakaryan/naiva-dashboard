"""DB queries for the competitors page. Only SQL here — no ER, averages or formatting."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import AccountDailyStats, Competitor, CompetitorDailyStats, CompetitorPost


class CompetitorRepository:
    def __init__(self, db: Session):
        self.db = db

    # ---------- competitors ----------

    def list(self, user_id: int) -> list[Competitor]:
        return list(self.db.scalars(
            select(Competitor).where(Competitor.user_id == user_id).order_by(Competitor.id)
        ))

    def get(self, user_id: int, competitor_id: int) -> Competitor | None:
        return self.db.scalar(
            select(Competitor).where(Competitor.user_id == user_id, Competitor.id == competitor_id)
        )

    def by_username(self, user_id: int, username: str) -> Competitor | None:
        return self.db.scalar(
            select(Competitor).where(Competitor.user_id == user_id,
                                     func.lower(Competitor.username) == username.lower())
        )

    def count(self, user_id: int) -> int:
        return self.db.scalar(select(func.count()).select_from(Competitor).where(Competitor.user_id == user_id)) or 0

    def add(self, competitor: Competitor) -> Competitor:
        self.db.add(competitor)
        self.db.flush()
        return competitor

    def remove(self, competitor: Competitor) -> None:
        cid = competitor.id
        self.db.execute(delete(CompetitorPost).where(CompetitorPost.competitor_id == cid))
        self.db.execute(delete(CompetitorDailyStats).where(CompetitorDailyStats.competitor_id == cid))
        self.db.delete(competitor)
        self.db.flush()

    def flush(self) -> None:
        self.db.flush()

    def commit(self) -> None:
        self.db.commit()

    # ---------- snapshots ----------

    def latest_snapshot(self, competitor_id: int, on_or_before: date) -> CompetitorDailyStats | None:
        return self.db.scalar(
            select(CompetitorDailyStats)
            .where(CompetitorDailyStats.competitor_id == competitor_id, CompetitorDailyStats.day <= on_or_before)
            .order_by(CompetitorDailyStats.day.desc()).limit(1)
        )

    def snapshot(self, competitor_id: int, day: date) -> CompetitorDailyStats | None:
        return self.db.scalar(
            select(CompetitorDailyStats)
            .where(CompetitorDailyStats.competitor_id == competitor_id, CompetitorDailyStats.day == day)
        )

    def my_followers(self, account_id: int, on_or_before: date) -> int | None:
        return self.db.scalar(
            select(AccountDailyStats.followers)
            .where(AccountDailyStats.ig_account_id == account_id, AccountDailyStats.day <= on_or_before)
            .order_by(AccountDailyStats.day.desc()).limit(1)
        )

    # ---------- posts ----------

    def posts(self, competitor_ids: list[int], since: datetime, until: datetime) -> list[CompetitorPost]:
        if not competitor_ids:
            return []
        return list(self.db.scalars(
            select(CompetitorPost)
            .where(CompetitorPost.competitor_id.in_(competitor_ids),
                   CompetitorPost.posted_at >= since, CompetitorPost.posted_at < until)
            .order_by(CompetitorPost.posted_at.desc())
        ))

    def posts_by_media_id(self, competitor_id: int) -> dict[str, CompetitorPost]:
        return {p.ig_media_id: p for p in self.db.scalars(
            select(CompetitorPost).where(CompetitorPost.competitor_id == competitor_id))}

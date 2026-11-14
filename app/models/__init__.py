"""All SQLAlchemy models. Import from here so every table is registered on Base.metadata."""
from app.models.analytics import (
    AccountDailyStats,
    AccountPeriodStats,
    AudienceOnlineHours,
    AudienceStats,
    Post,
    PostStats,
)
from app.models.competitor import Competitor, CompetitorDailyStats, CompetitorPost
from app.models.finance import Category, Deal, Transaction
from app.models.ig_account import IgAccount
from app.models.user import User

__all__ = [
    "User",
    "IgAccount",
    "AccountDailyStats",
    "AccountPeriodStats",
    "Post",
    "PostStats",
    "AudienceStats",
    "AudienceOnlineHours",
    "Category",
    "Deal",
    "Transaction",
    "Competitor",
    "CompetitorDailyStats",
    "CompetitorPost",
]

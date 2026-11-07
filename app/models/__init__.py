"""All SQLAlchemy models. Import from here so every table is registered on Base.metadata."""
from app.models.analytics import (
    AccountDailyStats,
    AudienceOnlineHours,
    AudienceStats,
    Post,
    PostStats,
)
from app.models.ig_account import IgAccount
from app.models.user import User

__all__ = [
    "User",
    "IgAccount",
    "AccountDailyStats",
    "Post",
    "PostStats",
    "AudienceStats",
    "AudienceOnlineHours",
]

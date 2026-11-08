from collections.abc import Iterator

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.models import IgAccount
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.finance_repository import FinanceRepository
from app.services.analytics_service import AnalyticsService
from app.services.finance_service import FinanceService
from core.database import SessionLocal

NO_ACCOUNT_MESSAGE = "Բազայում Instagram հաշիվ չկա։ Գործարկեք scripts/seed.py-ը դեմո տվյալների համար։"


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_optional_ig_account(db: Session = Depends(get_db)) -> IgAccount | None:
    """Until auth exists, the current account is the first one in the DB."""
    return AnalyticsRepository(db).get_current_account()


def get_current_ig_account(account: IgAccount | None = Depends(get_optional_ig_account)) -> IgAccount:
    if account is None:
        raise HTTPException(status_code=404, detail=NO_ACCOUNT_MESSAGE)
    return account


def get_analytics_service(
    db: Session = Depends(get_db),
    account: IgAccount = Depends(get_current_ig_account),
) -> AnalyticsService:
    return AnalyticsService(AnalyticsRepository(db), account)


def get_finance_service(
    db: Session = Depends(get_db),
    account: IgAccount = Depends(get_current_ig_account),
) -> FinanceService:
    # Finance belongs to the user, not to one Instagram account.
    return FinanceService(FinanceRepository(db), account.user_id)

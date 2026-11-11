import re
from typing import get_args

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_analytics_service
from app.schemas.analytics import ActiveHoursOut, AudienceOut, MonthPostsOut, PageOut, Period
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/page", response_model=PageOut)
def page(
    days: int = Query(30, description="7, 30 or 90"),
    service: AnalyticsService = Depends(get_analytics_service),
):
    """Everything the page needs for one period: hero + 12 metrics with chart points, posts."""
    if days not in get_args(Period):
        raise HTTPException(status_code=422, detail="days-ը պետք է լինի 7, 30 կամ 90")
    return service.page(days)


@router.get("/posts", response_model=MonthPostsOut)
def month_posts(
    month: str | None = Query(None, description="YYYY-MM; default: current month"),
    service: AnalyticsService = Depends(get_analytics_service),
):
    """Posts of one calendar month (Reels / Carousel / Post)."""
    if month is None:
        year, mon = service.today.year, service.today.month
    else:
        m = re.fullmatch(r"(\d{4})-(\d{2})", month)
        if not m or not 1 <= int(m.group(2)) <= 12:
            raise HTTPException(status_code=422, detail="month-ը պետք է լինի YYYY-MM ձևաչափով")
        year, mon = int(m.group(1)), int(m.group(2))
    return service.month_posts(year, mon)


@router.get("/audience", response_model=AudienceOut)
def audience(service: AnalyticsService = Depends(get_analytics_service)):
    return service.audience()


@router.get("/active-hours", response_model=ActiveHoursOut)
def active_hours(service: AnalyticsService = Depends(get_analytics_service)):
    return service.active_hours()

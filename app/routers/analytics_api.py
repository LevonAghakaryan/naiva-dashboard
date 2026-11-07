from fastapi import APIRouter, Depends, Query

from app.dependencies import get_analytics_service
from app.schemas.analytics import (
    ActiveHoursOut,
    AnalyticsType,
    AudienceOut,
    PostSort,
    PostsOut,
    ReachDailyOut,
    SummaryOut,
)
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/summary", response_model=SummaryOut)
def summary(
    days: int = Query(30, ge=1, le=365),
    type: AnalyticsType = Query("all"),
    service: AnalyticsService = Depends(get_analytics_service),
):
    return service.summary(type, days)


@router.get("/reach-daily", response_model=ReachDailyOut)
def reach_daily(
    days: int = Query(14, ge=1, le=90),
    service: AnalyticsService = Depends(get_analytics_service),
):
    return service.reach_daily(days)


@router.get("/audience", response_model=AudienceOut)
def audience(service: AnalyticsService = Depends(get_analytics_service)):
    return service.audience()


@router.get("/active-hours", response_model=ActiveHoursOut)
def active_hours(service: AnalyticsService = Depends(get_analytics_service)):
    return service.active_hours()


@router.get("/posts", response_model=PostsOut)
def posts(
    type: AnalyticsType = Query("all"),
    sort: PostSort = Query("views"),
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(50, ge=1, le=200),
    service: AnalyticsService = Depends(get_analytics_service),
):
    return service.posts(type, sort, days, limit)
